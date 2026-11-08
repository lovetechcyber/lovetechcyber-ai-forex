from pymongo import ASCENDING, DESCENDING, AsyncMongoClient
from pymongo.errors import PyMongoError

from app.core.config import settings


client: AsyncMongoClient | None = None


# =========================================================
# MongoDB Connection
# =========================================================

async def connect_to_mongodb() -> None:
    global client

    new_client = AsyncMongoClient(
        settings.mongodb_uri,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
        socketTimeoutMS=10000,
        maxPoolSize=20,
        minPoolSize=1,
        retryReads=True,
        retryWrites=True,
        tz_aware=True,
    )

    try:
        # 1. Verify MongoDB connectivity.
        await new_client.admin.command("ping")

        # 2. Initialize the database BEFORE creating indexes.
        database = new_client[settings.mongodb_database]

        # =================================================
        # User Indexes
        # =================================================

        await database.users.create_index(
            [("email", ASCENDING)],
            unique=True,
            name="unique_user_email",
        )

        # =================================================
        # Refresh Token Indexes
        # =================================================

        await database.refresh_tokens.create_index(
            [("token_hash", ASCENDING)],
            unique=True,
            name="unique_refresh_token_hash",
        )

        await database.refresh_tokens.create_index(
            [("family_id", ASCENDING)],
            name="refresh_token_family",
        )

        await database.refresh_tokens.create_index(
            [("expires_at", ASCENDING)],
            expireAfterSeconds=0,
            name="refresh_token_ttl",
        )

        # =================================================
        # Password Reset Indexes
        # =================================================

        await database.password_reset_tokens.create_index(
            [("token_hash", ASCENDING)],
            unique=True,
            name="unique_password_reset_hash",
        )

        await database.password_reset_tokens.create_index(
            [("expires_at", ASCENDING)],
            expireAfterSeconds=0,
            name="password_reset_ttl",
        )

        await database.password_reset_tokens.create_index(
            [("user_id", ASCENDING)],
            name="password_reset_user",
        )

        # =================================================
        # Market Data Indexes
        # =================================================

        await database.market_candles.create_index(
            [
                ("symbol", ASCENDING),
                ("timeframe", ASCENDING),
                ("timestamp", ASCENDING),
            ],
            unique=True,
            name="unique_market_candle",
        )

        await database.market_candles.create_index(
            [
                ("symbol", ASCENDING),
                ("timeframe", ASCENDING),
                ("timestamp", DESCENDING),
            ],
            name="market_candle_latest",
        )
        
        await database.analysis_history.create_index(
            [
                ("user_id", ASCENDING),
                ("analyzed_at", DESCENDING),
            ],
            name="analysis_history_user_date",
        )

        await database.analysis_history.create_index(
            [
                ("user_id", ASCENDING),
                ("symbol", ASCENDING),
                ("timeframe", ASCENDING),
                ("analyzed_at", DESCENDING),
            ],
            name="analysis_history_user_symbol_timeframe",
        )

        await database.analysis_history.create_index(
            [
                ("user_id", ASCENDING),
                ("directional_bias", ASCENDING),
                ("analyzed_at", DESCENDING),
            ],
            name="analysis_history_user_bias",
        )

        # 3. Publish the client only after all initialization succeeds.
        client = new_client

        print("MongoDB connected successfully.")
        print("MongoDB indexes initialized successfully.")

    except PyMongoError:
        await new_client.close()
        raise RuntimeError(
            "MongoDB connection or index initialization failed"
        ) from None

    except Exception:
        await new_client.close()
        raise


# =========================================================
# Database Access
# =========================================================

def get_database():
    if client is None:
        raise RuntimeError(
            "MongoDB is not initialized. "
            "Check the application lifespan."
        )

    return client[settings.mongodb_database]


# =========================================================
# MongoDB Shutdown
# =========================================================

async def close_mongodb_connection() -> None:
    global client

    if client is not None:
        await client.close()
        client = None

        print("MongoDB connection closed.")


# =========================================================
# Database Health Check
# =========================================================

async def check_database_health() -> bool:
    if client is None:
        return False

    try:
        await client.admin.command("ping")
        return True

    except PyMongoError:
        return False