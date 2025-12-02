#!/usr/bin/env python3
"""
Database connection monitoring script.

Monitors PostgreSQL connection state and reports issues.
Run periodically to track database health.
"""

import asyncio
import sys
from datetime import datetime

import asyncpg
from loguru import logger


async def check_db_connections(
    host: str = "localhost",
    port: int = 5432,
    user: str = "sigmatrade",
    password: str = "SecurePass2024",
    database: str = "sigmatrade",
) -> dict[str, any]:
    """
    Check database connection state.
    
    Returns:
        dict: Connection statistics
    """
    try:
        conn = await asyncpg.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
        )
        
        # Get connection statistics
        stats_query = """
        SELECT 
            application_name,
            state,
            COUNT(*) as count,
            MAX(NOW() - state_change) as max_idle,
            MAX(NOW() - xact_start) as max_transaction_age
        FROM pg_stat_activity 
        WHERE datname = $1
        GROUP BY application_name, state
        ORDER BY count DESC;
        """
        
        stats = await conn.fetch(stats_query, database)
        
        # Get total connections
        total_query = """
        SELECT 
            COUNT(*) as total,
            (SELECT setting::int FROM pg_settings WHERE name = 'max_connections') as max_conn
        FROM pg_stat_activity 
        WHERE datname = $1;
        """
        
        total_info = await conn.fetchrow(total_query, database)
        
        # Get longest running queries
        long_queries = """
        SELECT 
            pid,
            NOW() - query_start as duration,
            state,
            query
        FROM pg_stat_activity
        WHERE datname = $1 AND state != 'idle'
        ORDER BY duration DESC
        LIMIT 5;
        """
        
        queries = await conn.fetch(long_queries, database)
        
        await conn.close()
        
        return {
            "stats": stats,
            "total": total_info,
            "long_queries": queries,
            "timestamp": datetime.now(),
        }
        
    except Exception as e:
        logger.error(f"Failed to check DB connections: {e}")
        return None


def analyze_and_report(data: dict) -> tuple[bool, list[str]]:
    """
    Analyze connection data and generate warnings.
    
    Returns:
        tuple: (is_healthy, list of warnings)
    """
    warnings = []
    is_healthy = True
    
    if not data:
        return False, ["Failed to connect to database"]
    
    total_info = data["total"]
    total_conn = total_info["total"]
    max_conn = total_info["max_conn"]
    
    # Check total connections
    conn_usage = (total_conn / max_conn) * 100
    if conn_usage > 80:
        warnings.append(
            f"⚠️  HIGH CONNECTION USAGE: {total_conn}/{max_conn} ({conn_usage:.1f}%)"
        )
        is_healthy = False
    elif conn_usage > 60:
        warnings.append(
            f"⚡ Warning: Connection usage at {conn_usage:.1f}% ({total_conn}/{max_conn})"
        )
    
    # Check idle in transaction
    for stat in data["stats"]:
        if stat["state"] == "idle in transaction":
            count = stat["count"]
            max_idle = stat["max_idle"]
            
            if max_idle and max_idle.total_seconds() > 300:  # 5 minutes
                warnings.append(
                    f"🔴 CRITICAL: {count} connections in 'idle in transaction' "
                    f"for up to {max_idle}"
                )
                is_healthy = False
            elif max_idle and max_idle.total_seconds() > 60:  # 1 minute
                warnings.append(
                    f"⚠️  Warning: {count} connections in 'idle in transaction' "
                    f"for up to {max_idle}"
                )
    
    # Check long-running queries
    for query in data["long_queries"]:
        duration = query["duration"]
        if duration.total_seconds() > 30:
            warnings.append(
                f"⏱️  Long query detected: {duration} - "
                f"PID {query['pid']}, State: {query['state']}"
            )
    
    return is_healthy, warnings


def print_report(data: dict, is_healthy: bool, warnings: list[str]) -> None:
    """Print formatted report."""
    print("\n" + "=" * 60)
    print(f"📊 Database Connection Monitor - {data['timestamp']}")
    print("=" * 60)
    
    total_info = data["total"]
    print(f"\n📈 Total Connections: {total_info['total']}/{total_info['max_conn']}")
    
    print("\n📋 Connection State Breakdown:")
    print("-" * 60)
    for stat in data["stats"]:
        app_name = stat["application_name"] or "(no app)"
        state = stat["state"]
        count = stat["count"]
        max_idle = stat["max_idle"] or "N/A"
        
        print(f"  {app_name:15} | {state:20} | Count: {count:3} | Max Idle: {max_idle}")
    
    if warnings:
        print("\n🚨 WARNINGS:")
        print("-" * 60)
        for warning in warnings:
            print(f"  {warning}")
    
    if is_healthy:
        print("\n✅ Database connections are healthy!")
    else:
        print("\n❌ Database connection issues detected!")
    
    print("=" * 60 + "\n")


async def main():
    """Main entry point."""
    # Parse command line args for remote monitoring
    host = sys.argv[1] if len(sys.argv) > 1 else "localhost"
    
    logger.info(f"Checking database connections on {host}...")
    
    data = await check_db_connections(host=host)
    
    if data:
        is_healthy, warnings = analyze_and_report(data)
        print_report(data, is_healthy, warnings)
        
        # Exit with error code if unhealthy
        sys.exit(0 if is_healthy else 1)
    else:
        logger.error("Failed to retrieve database statistics")
        sys.exit(2)


if __name__ == "__main__":
    asyncio.run(main())
