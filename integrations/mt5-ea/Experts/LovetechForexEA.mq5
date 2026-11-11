// LovetechForexEA.mq5
// Initial analysis-only EA placeholder.
// No trading functions are implemented.


#property strict
#property strict
#property version   "1.20"
#property description "LovetechCyber AI Forex Analyst - Market Data Collector"

//==================================================
// INPUT SETTINGS
//==================================================

input string InpApiUrl = "https://lovetechcyber-ai-forex.onrender.com/api/v1/market-data/ingest";
input string InpApiKey = "";
input int    InpCandlesPerBatch = 200;
input int    InpTimerSeconds = 3;
input int    InpRequestTimeoutMs = 15000;
input int    InpSymbolRefreshMinutes = 60;

//==================================================
// GLOBAL VARIABLES
//==================================================

ENUM_TIMEFRAMES Timeframes[] =
{
   PERIOD_M5,
   PERIOD_M15,
   PERIOD_M30,
   PERIOD_H1,
   PERIOD_H4,
   PERIOD_D1
};

string TimeframeNames[] =
{
   "M5", "M15", "M30", "H1", "H4", "D1"
};

string ForexSymbols[];

int SymbolCount = 0;
int CurrentSymbolIndex = 0;
int CurrentTimeframeIndex = 0;

datetime LastScanCompleted = 0;
datetime LastSymbolRefresh = 0;

string CurrentStatus = "Initializing";

//==================================================
// VALIDATE API-COMPATIBLE SYMBOL NAME
//==================================================

bool IsApiCompatibleSymbol(string symbol)
{
   int length = StringLen(symbol);

   if(length < 3 || length > 30)
      return false;

   for(int i = 0; i < length; i++)
   {
      ushort character = StringGetCharacter(symbol, i);

      bool valid =
         (character >= 48 && character <= 57)  || // 0-9
         (character >= 65 && character <= 90)  || // A-Z
         (character >= 97 && character <= 122) || // a-z
         character == 46 ||                       // .
         character == 95 ||                       // _
         character == 45;                         // -

      if(!valid)
         return false;
   }

   return true;
}

//==================================================
// CHECK WHETHER SYMBOL IS FOREX
//==================================================

bool IsForexSymbol(string symbol)
{
   long calculationMode = -1;

   if(!SymbolInfoInteger(
      symbol,
      SYMBOL_TRADE_CALC_MODE,
      calculationMode
   ))
   {
      return false;
   }

   return (
      calculationMode == SYMBOL_CALC_MODE_FOREX ||
      calculationMode == SYMBOL_CALC_MODE_FOREX_NO_LEVERAGE
   );
}

//==================================================
// DISCOVER BROKER FOREX SYMBOLS
//==================================================

void DiscoverForexSymbols()
{
   ArrayResize(ForexSymbols, 0);

   SymbolCount = 0;

   int total = SymbolsTotal(false);

   for(int i = 0; i < total; i++)
   {
      string symbol = SymbolName(i, false);

      if(symbol == "")
         continue;

      if(!IsForexSymbol(symbol))
         continue;

      if(!IsApiCompatibleSymbol(symbol))
      {
         Print(
            "Skipping unsupported symbol name: ",
            symbol
         );

         continue;
      }

      if(!SymbolSelect(symbol, true))
      {
         Print(
            "Could not select symbol: ",
            symbol
         );

         continue;
      }

      int newSize = ArrayResize(
         ForexSymbols,
         SymbolCount + 1
      );

      if(newSize != SymbolCount + 1)
      {
         Print("Failed to resize forex symbol array.");
         break;
      }

      ForexSymbols[SymbolCount] = symbol;

      SymbolCount++;
   }

   CurrentSymbolIndex = 0;
   CurrentTimeframeIndex = 0;

   LastSymbolRefresh = TimeCurrent();

   Print(
      "Forex symbols discovered: ",
      SymbolCount
   );
}

//==================================================
// BUILD CANDLE JSON PAYLOAD
//==================================================

string BuildCandlePayload(
   string symbol,
   ENUM_TIMEFRAMES timeframe,
   string timeframeName
)
{
   MqlRates rates[];

   ArraySetAsSeries(rates, true);

   ResetLastError();

   int copied = CopyRates(
      symbol,
      timeframe,
      1,
      InpCandlesPerBatch,
      rates
   );

   if(copied <= 0)
   {
      Print(
         "No candle data for ",
         symbol,
         " ",
         timeframeName,
         ". Error: ",
         GetLastError()
      );

      return "";
   }

   int digits = (int)SymbolInfoInteger(
      symbol,
      SYMBOL_DIGITS
   );

   string json =
      "{\"symbol\":\"" + symbol +
      "\",\"timeframe\":\"" + timeframeName +
      "\",\"candles\":[";

   // IMPORTANT:
   // ArraySetAsSeries(true) means logical index 0 is newest.
   // Send candles in ascending timestamp order:
   // oldest first, newest last.

   for(int i = copied - 1; i >= 0; i--)
   {
      if(i < copied - 1)
         json += ",";

      json += "{";

      json += "\"timestamp\":" +
         IntegerToString((long)rates[i].time) + ",";

      json += "\"open\":" +
         DoubleToString(rates[i].open, digits) + ",";

      json += "\"high\":" +
         DoubleToString(rates[i].high, digits) + ",";

      json += "\"low\":" +
         DoubleToString(rates[i].low, digits) + ",";

      json += "\"close\":" +
         DoubleToString(rates[i].close, digits) + ",";

      json += "\"tick_volume\":" +
         IntegerToString((long)rates[i].tick_volume) + ",";

      json += "\"spread\":" +
         IntegerToString((int)rates[i].spread) + ",";

      json += "\"real_volume\":" +
         IntegerToString((long)rates[i].real_volume);

      json += "}";
   }

   json += "]}";

   return json;
}

//==================================================
// SEND MARKET DATA TO FASTAPI
//==================================================

bool SendMarketData(
   string payload,
   string symbol,
   string timeframe
)
{
   if(payload == "")
      return false;

   char postData[];
   char responseData[];

   int bytes = StringToCharArray(
      payload,
      postData,
      0,
      WHOLE_ARRAY,
      CP_UTF8
   );

   if(bytes <= 1)
   {
      Print("Failed to encode market data.");

      return false;
   }

   // Remove terminating null byte.

   if(ArrayResize(postData, bytes - 1) != bytes - 1)
   {
      Print("Failed to resize HTTP request buffer.");

      return false;
   }

   string headers =
      "Content-Type: application/json\r\n" +
      "X-MT5-API-Key: " + InpApiKey + "\r\n";

   string responseHeaders;

   ResetLastError();

   int httpStatus = WebRequest(
      "POST",
      InpApiUrl,
      headers,
      InpRequestTimeoutMs,
      postData,
      responseData,
      responseHeaders
   );

   // Handle network or MT5 WebRequest failure.

   if(httpStatus == -1)
   {
      int errorCode = GetLastError();

      Print(
         "TRANSMISSION ERROR | ",
         symbol,
         " | ",
         timeframe,
         " | MT5 Error: ",
         errorCode
      );

      CurrentStatus = "API transmission failed";

      return false;
   }

   string responseText = CharArrayToString(
      responseData,
      0,
      -1,
      CP_UTF8
   );

   // Successful ingestion.

   if(httpStatus == 202)
   {
      Print(
         "MARKET DATA ACCEPTED | ",
         symbol,
         " | ",
         timeframe,
         " | ",
         responseText
      );

      CurrentStatus = "Data accepted by API";

      return true;
   }

   // Detailed validation logging.

   if(httpStatus == 422)
   {
      Print(
         "VALIDATION ERROR 422 | ",
         symbol,
         " | ",
         timeframe,
         " | API Details: ",
         responseText
      );
   }
   else
   {
      Print(
         "API REJECTION | HTTP ",
         httpStatus,
         " | ",
         symbol,
         " | ",
         timeframe,
         " | Response: ",
         responseText
      );
   }

   CurrentStatus = "API rejected market data";

   return false;
}

//==================================================
// PROCESS ONE MARKET DATA JOB
//==================================================

void ProcessNextJob()
{
   if(SymbolCount <= 0)
   {
      CurrentStatus = "No forex symbols found";

      UpdateChartStatus();

      return;
   }

   if(CurrentSymbolIndex >= SymbolCount)
      CurrentSymbolIndex = 0;

   if(CurrentTimeframeIndex >= ArraySize(Timeframes))
      CurrentTimeframeIndex = 0;

   string symbol = ForexSymbols[CurrentSymbolIndex];

   ENUM_TIMEFRAMES timeframe =
      Timeframes[CurrentTimeframeIndex];

   string timeframeName =
      TimeframeNames[CurrentTimeframeIndex];

   CurrentStatus =
      "Scanning " + symbol + " " + timeframeName;

   string payload = BuildCandlePayload(
      symbol,
      timeframe,
      timeframeName
   );

   if(payload != "")
   {
      SendMarketData(
         payload,
         symbol,
         timeframeName
      );
   }

   // Advance timeframe.

   CurrentTimeframeIndex++;

   if(CurrentTimeframeIndex >= ArraySize(Timeframes))
   {
      CurrentTimeframeIndex = 0;

      CurrentSymbolIndex++;
   }

   // Complete full symbol cycle.

   if(CurrentSymbolIndex >= SymbolCount)
   {
      CurrentSymbolIndex = 0;

      LastScanCompleted = TimeCurrent();

      CurrentStatus = "Scan cycle completed";

      Print(
         "All forex symbol/timeframe jobs processed."
      );
   }

   UpdateChartStatus();
}

//==================================================
// UPDATE CHART STATUS
//==================================================

void UpdateChartStatus()
{
   string lastCycle = "Not completed";

   if(LastScanCompleted > 0)
   {
      lastCycle = TimeToString(
         LastScanCompleted,
         TIME_DATE | TIME_SECONDS
      );
   }

   string status =
      "LOVETECHCYBER AI FOREX ANALYST\n"
      "--------------------------------\n"
      "Mode: Market Analysis Only\n"
      "Forex Symbols: " + IntegerToString(SymbolCount) + "\n"
      "Timeframes: 6\n"
      "Status: " + CurrentStatus + "\n"
      "Last Cycle: " + lastCycle + "\n"
      "API: " + InpApiUrl;

   Comment(status);
}

//==================================================
// EXPERT ADVISOR INITIALIZATION
//==================================================

int OnInit()
{
   if(StringLen(InpApiKey) < 32)
   {
      Print(
         "ERROR: Configure a valid MT5 ingestion API key."
      );

      return INIT_PARAMETERS_INCORRECT;
   }

   if(StringLen(InpApiUrl) < 10)
   {
      Print("ERROR: Invalid API URL.");

      return INIT_PARAMETERS_INCORRECT;
   }

   if(InpCandlesPerBatch < 1 || InpCandlesPerBatch > 500)
   {
      Print(
         "ERROR: Candle batch must be between 1 and 500."
      );

      return INIT_PARAMETERS_INCORRECT;
   }

   if(InpTimerSeconds < 3)
   {
      Print(
         "ERROR: Timer interval must be at least 3 seconds."
      );

      return INIT_PARAMETERS_INCORRECT;
   }

   if(InpRequestTimeoutMs < 1000)
   {
      Print(
         "ERROR: Request timeout must be at least 1000 ms."
      );

      return INIT_PARAMETERS_INCORRECT;
   }

   DiscoverForexSymbols();

   if(SymbolCount <= 0)
   {
      Print(
         "No supported forex symbols are currently available."
      );

      return INIT_FAILED;
   }

   if(!EventSetTimer(InpTimerSeconds))
   {
      Print(
         "Failed to initialize timer. Error: ",
         GetLastError()
      );

      return INIT_FAILED;
   }

   CurrentStatus = "MT5 collector initialized";

   UpdateChartStatus();

   Print(
      "LovetechForexEA initialized successfully."
   );

   return INIT_SUCCEEDED;
}

//==================================================
// TIMER EVENT
//==================================================

void OnTimer()
{
   // Periodically refresh broker symbols.

   if(
      InpSymbolRefreshMinutes > 0 &&
      TimeCurrent() - LastSymbolRefresh >=
      InpSymbolRefreshMinutes * 60
   )
   {
      DiscoverForexSymbols();
   }

   ProcessNextJob();
}

//==================================================
// TICK EVENT
//==================================================

void OnTick()
{
   // Analysis-only application.
   // No order placement, modification or closure.
   // Collection is timer-driven.
}

//==================================================
// EXPERT ADVISOR SHUTDOWN
//==================================================

void OnDeinit(const int reason)
{
   EventKillTimer();

   Comment("");

   Print(
      "LovetechForexEA stopped. Reason: ",
      reason
   );
}
