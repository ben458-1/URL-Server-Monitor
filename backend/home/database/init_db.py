import psycopg2
from psycopg2 import sql
import os
from dotenv import load_dotenv

load_dotenv()

DB_SCHEMA = os.getenv('DB_SCHEMA', 'gpu_monitor')
DEFAULT_GPU_USAGE_LIMIT = int(os.getenv('DEFAULT_GPU_USAGE_LIMIT', '80'))

DATABASE_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'URL_Healthcheck'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'postgres')
}

def create_tables():
    """Create all database tables in schema from environment variable"""
    
    # Create schema
    create_schema = sql.SQL("""
        CREATE SCHEMA IF NOT EXISTS {schema};
    """).format(schema=sql.Identifier(DB_SCHEMA))
    
    # Set search path
    set_search_path = sql.SQL("""
        SET search_path TO {schema}, public;
    """).format(schema=sql.Identifier(DB_SCHEMA))
    
    # SQL statements to create tables
    create_projects_table = sql.SQL("""
        CREATE TABLE IF NOT EXISTS {schema}.projects (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """).format(schema=sql.Identifier(DB_SCHEMA))
    
    create_servers_table = sql.SQL("""
        CREATE TABLE IF NOT EXISTS {schema}.servers (
            id SERIAL PRIMARY KEY,
            server_name VARCHAR(255) UNIQUE NOT NULL,
            port INTEGER,
            server_location VARCHAR(100) NOT NULL CHECK (server_location IN ('India', 'Estonia')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """).format(schema=sql.Identifier(DB_SCHEMA))
    
    create_urls_table = sql.SQL("""
        CREATE TABLE IF NOT EXISTS {schema}.urls (
            id SERIAL PRIMARY KEY,
            project_name VARCHAR(255) NOT NULL,
            url TEXT NOT NULL,
            environment VARCHAR(50) NOT NULL CHECK (environment IN ('production', 'development', 'staging')),
            project_category VARCHAR(255),
            server_id INTEGER REFERENCES {schema}.servers(id) ON DELETE SET NULL,
            health_check_status VARCHAR(3) DEFAULT 'YES' CHECK (health_check_status IN ('YES', 'NO')),
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_category) REFERENCES {schema}.projects(name) ON DELETE SET NULL
        );
    """).format(schema=sql.Identifier(DB_SCHEMA))
    
    create_health_status_table = sql.SQL("""
        CREATE TABLE IF NOT EXISTS {schema}.health_status (
            id SERIAL PRIMARY KEY,
            url_id INTEGER NOT NULL REFERENCES {schema}.urls(id) ON DELETE CASCADE,
            status VARCHAR(20) NOT NULL CHECK (status IN ('online', 'offline')),
            response_time INTEGER,
            status_code INTEGER,
            checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            error_message TEXT
        );
    """).format(schema=sql.Identifier(DB_SCHEMA))
    
    create_gpu_metrics_table = sql.SQL("""
        CREATE TABLE IF NOT EXISTS {schema}.gpu_metrics (
            id SERIAL PRIMARY KEY,
            host VARCHAR(255) NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            gpu_index INTEGER NOT NULL,
            gpu_name VARCHAR(255) NOT NULL,
            gpu_memory_total_mib INTEGER NOT NULL,
            gpu_memory_used_mib INTEGER NOT NULL,
            gpu_memory_free_mib INTEGER NOT NULL,
            gpu_utilization_pct INTEGER NOT NULL,
            host_memory_total_mib INTEGER NOT NULL,
            host_memory_used_mib INTEGER NOT NULL,
            host_memory_free_mib INTEGER NOT NULL,
            host_disk_total_mib INTEGER DEFAULT 0,
            host_disk_used_mib INTEGER DEFAULT 0,
            host_disk_free_mib INTEGER DEFAULT 0,
            host_disk_usage_pct INTEGER DEFAULT 0
        );
    """).format(schema=sql.Identifier(DB_SCHEMA))
    
    create_pid_metrics_table = sql.SQL("""
        CREATE TABLE IF NOT EXISTS {schema}.pid_metrics (
            id SERIAL PRIMARY KEY,
            gpu_metrics_id INTEGER NOT NULL REFERENCES {schema}.gpu_metrics(id) ON DELETE CASCADE,
            pid INTEGER NOT NULL,
            process_name VARCHAR(500) NOT NULL,
            cmd TEXT,
            used_mem_mib INTEGER NOT NULL,
            process_ram_mib INTEGER DEFAULT 0,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """).format(schema=sql.Identifier(DB_SCHEMA))
    
    # GPU Server table with encryption support
    create_gpu_server_table = sql.SQL("""
        CREATE TABLE IF NOT EXISTS {schema}.gpu_server (
            id SERIAL PRIMARY KEY,
            server_ip VARCHAR(45) NOT NULL,
            server_name VARCHAR(255) UNIQUE NOT NULL,
            gpu_name VARCHAR(255),
            username VARCHAR(255) NOT NULL,
            port INTEGER NOT NULL,
            rsa_key TEXT NOT NULL,
            rsa_key_passphrase TEXT,
            server_location VARCHAR(100),
            usage_limit INTEGER DEFAULT {default_limit} CHECK (usage_limit >= 0 AND usage_limit <= 100),
            alert_emails JSONB DEFAULT '[]'::jsonb,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """).format(
        schema=sql.Identifier(DB_SCHEMA),
        default_limit=sql.Literal(DEFAULT_GPU_USAGE_LIMIT)
    )
    
    # GPU Alert History table
    create_gpu_alert_history_table = sql.SQL("""
        CREATE TABLE IF NOT EXISTS {schema}.gpu_alert_history (
            id SERIAL PRIMARY KEY,
            server_id INTEGER NOT NULL REFERENCES {schema}.gpu_server(id) ON DELETE CASCADE,
            gpu_index INTEGER NOT NULL,
            usage_pct NUMERIC(5,2) NOT NULL,
            memory_used_mib INTEGER NOT NULL,
            memory_total_mib INTEGER NOT NULL,
            threshold_pct INTEGER NOT NULL,
            recipient_emails JSONB NOT NULL,
            sent_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """).format(schema=sql.Identifier(DB_SCHEMA))
    
    # User management tables
    create_roles_table = sql.SQL("""
        CREATE TABLE IF NOT EXISTS {schema}.roles (
            id SERIAL PRIMARY KEY,
            role_name VARCHAR(50) UNIQUE NOT NULL,
            display_name VARCHAR(100) NOT NULL,
            description TEXT,
            can_view_urls BOOLEAN DEFAULT true,
            can_add_urls BOOLEAN DEFAULT false,
            can_edit_urls BOOLEAN DEFAULT false,
            can_delete_urls BOOLEAN DEFAULT false,
            can_view_servers BOOLEAN DEFAULT true,
            can_add_servers BOOLEAN DEFAULT false,
            can_edit_servers BOOLEAN DEFAULT false,
            can_delete_servers BOOLEAN DEFAULT false,
            can_view_gpu_stats BOOLEAN DEFAULT true,
            can_manage_email_alerts BOOLEAN DEFAULT false,
            can_manage_users BOOLEAN DEFAULT false,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """).format(schema=sql.Identifier(DB_SCHEMA))
    
    create_users_table = sql.SQL("""
        CREATE TABLE IF NOT EXISTS {schema}.users (
            email VARCHAR(255) PRIMARY KEY,
            name VARCHAR(255),
            azure_user_id VARCHAR(255) UNIQUE NOT NULL,
            role VARCHAR(50) DEFAULT 'viewer' NOT NULL,
            is_active BOOLEAN DEFAULT true,
            last_login TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_user_role FOREIGN KEY (role) REFERENCES {schema}.roles(role_name) ON UPDATE CASCADE
        );
    """).format(schema=sql.Identifier(DB_SCHEMA))
    
    # user_activity_log table removed - not needed
    
    # Create indexes
    create_indexes = [
        sql.SQL("CREATE INDEX IF NOT EXISTS idx_health_url_id ON {schema}.health_status(url_id);").format(schema=sql.Identifier(DB_SCHEMA)),
        sql.SQL("CREATE INDEX IF NOT EXISTS idx_health_checked_at ON {schema}.health_status(checked_at);").format(schema=sql.Identifier(DB_SCHEMA)),
        sql.SQL("CREATE INDEX IF NOT EXISTS idx_urls_environment ON {schema}.urls(environment);").format(schema=sql.Identifier(DB_SCHEMA)),
        sql.SQL("CREATE INDEX IF NOT EXISTS idx_urls_project_category ON {schema}.urls(project_category);").format(schema=sql.Identifier(DB_SCHEMA)),
        sql.SQL("CREATE INDEX IF NOT EXISTS idx_gpu_server_name ON {schema}.gpu_server(server_name);").format(schema=sql.Identifier(DB_SCHEMA)),
        sql.SQL("CREATE INDEX IF NOT EXISTS idx_gpu_metrics_host_gpu ON {schema}.gpu_metrics(host, gpu_index, timestamp DESC);").format(schema=sql.Identifier(DB_SCHEMA)),
        sql.SQL("CREATE INDEX IF NOT EXISTS idx_pid_metrics_gpu_id ON {schema}.pid_metrics(gpu_metrics_id);").format(schema=sql.Identifier(DB_SCHEMA)),
        sql.SQL("CREATE INDEX IF NOT EXISTS idx_gpu_alert_history_server_gpu_time ON {schema}.gpu_alert_history(server_id, gpu_index, sent_at DESC);").format(schema=sql.Identifier(DB_SCHEMA)),
        sql.SQL("CREATE INDEX IF NOT EXISTS idx_users_azure_id ON {schema}.users(azure_user_id);").format(schema=sql.Identifier(DB_SCHEMA)),
        sql.SQL("CREATE INDEX IF NOT EXISTS idx_users_role ON {schema}.users(role);").format(schema=sql.Identifier(DB_SCHEMA))
    ]
    
    # Insert default roles
    insert_default_roles = sql.SQL("""
        INSERT INTO {schema}.roles (role_name, display_name, description,
            can_view_urls, can_add_urls, can_edit_urls, can_delete_urls,
            can_view_servers, can_add_servers, can_edit_servers, can_delete_servers,
            can_view_gpu_stats, can_manage_email_alerts, can_manage_users)
        VALUES
            ('owner', 'Owner', 'Full system access with all permissions',
             true, true, true, true, true, true, true, true, true, true, true),
            ('admin', 'Administrator', 'Can manage all resources including users',
             true, true, true, true, true, true, true, true, true, true, true),
            ('editor', 'Editor', 'Can view and edit resources',
             true, true, true, false, true, true, true, false, true, false, false),
            ('viewer', 'Viewer', 'Can only view resources',
             true, false, false, false, true, false, false, false, true, false, false)
        ON CONFLICT (role_name) DO NOTHING;
    """).format(schema=sql.Identifier(DB_SCHEMA))
    
    # Create trigger functions
    create_trigger_function = sql.SQL("""
        CREATE OR REPLACE FUNCTION {schema}.update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """).format(schema=sql.Identifier(DB_SCHEMA))
    
    create_trigger_function_last_updated = sql.SQL("""
        CREATE OR REPLACE FUNCTION {schema}.update_last_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.last_updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """).format(schema=sql.Identifier(DB_SCHEMA))
    
    # Create trigger
    create_trigger = sql.SQL("""
        DROP TRIGGER IF EXISTS update_urls_updated_at ON {schema}.urls;
        CREATE TRIGGER update_urls_updated_at 
            BEFORE UPDATE ON {schema}.urls
            FOR EACH ROW
            EXECUTE FUNCTION {schema}.update_updated_at_column();
    """).format(schema=sql.Identifier(DB_SCHEMA))
    
    
    try:
        # Connect to database
        conn = psycopg2.connect(**DATABASE_CONFIG)
        cursor = conn.cursor()
        
        print(f"Creating schema {DB_SCHEMA}...")
        cursor.execute(create_schema)
        print(f"[OK] Created schema {DB_SCHEMA}")
        
        print("Setting search path...")
        cursor.execute(set_search_path)
        
        print("Creating tables...")
        
        # Create tables
        cursor.execute(create_projects_table)
        print(f"[OK] Created {DB_SCHEMA}.projects table")
        
        cursor.execute(create_servers_table)
        print(f"[OK] Created {DB_SCHEMA}.servers table")
        
        cursor.execute(create_urls_table)
        print(f"[OK] Created {DB_SCHEMA}.urls table")
        
        cursor.execute(create_health_status_table)
        print(f"[OK] Created {DB_SCHEMA}.health_status table")
        
        cursor.execute(create_gpu_metrics_table)
        print(f"[OK] Created {DB_SCHEMA}.gpu_metrics table")
        
        cursor.execute(create_pid_metrics_table)
        print(f"[OK] Created {DB_SCHEMA}.pid_metrics table")
        
        cursor.execute(create_gpu_server_table)
        print(f"[OK] Created {DB_SCHEMA}.gpu_server table")
        
        cursor.execute(create_gpu_alert_history_table)
        print(f"[OK] Created {DB_SCHEMA}.gpu_alert_history table")
        
        cursor.execute(create_roles_table)
        print(f"[OK] Created {DB_SCHEMA}.roles table")
        
        cursor.execute(create_users_table)
        print(f"[OK] Created {DB_SCHEMA}.users table")
        
        # Insert default roles
        print("Inserting default roles...")
        cursor.execute(insert_default_roles)
        print("[OK] Inserted default roles")
        
        # Create indexes
        print("Creating indexes...")
        for index_sql in create_indexes:
            cursor.execute(index_sql)
        print("[OK] Created indexes")
        
        # Create trigger functions and triggers
        print("Creating triggers...")
        cursor.execute(create_trigger_function)
        cursor.execute(create_trigger_function_last_updated)
        cursor.execute(create_trigger)
        
        # Create trigger for servers table
        create_servers_trigger = sql.SQL("""
            DROP TRIGGER IF EXISTS update_servers_updated_at ON {schema}.servers;
            CREATE TRIGGER update_servers_updated_at
                BEFORE UPDATE ON {schema}.servers
                FOR EACH ROW
                EXECUTE FUNCTION {schema}.update_updated_at_column();
        """).format(schema=sql.Identifier(DB_SCHEMA))
        cursor.execute(create_servers_trigger)
        
        # Create trigger for users table
        create_users_trigger = sql.SQL("""
            DROP TRIGGER IF EXISTS update_users_updated_at ON {schema}.users;
            CREATE TRIGGER update_users_updated_at
                BEFORE UPDATE ON {schema}.users
                FOR EACH ROW
                EXECUTE FUNCTION {schema}.update_updated_at_column();
        """).format(schema=sql.Identifier(DB_SCHEMA))
        cursor.execute(create_users_trigger)
        
        # Create trigger for gpu_server table
        create_gpu_server_trigger = sql.SQL("""
            DROP TRIGGER IF EXISTS update_gpu_server_last_updated_at ON {schema}.gpu_server;
            CREATE TRIGGER update_gpu_server_last_updated_at
                BEFORE UPDATE ON {schema}.gpu_server
                FOR EACH ROW
                EXECUTE FUNCTION {schema}.update_last_updated_at_column();
        """).format(schema=sql.Identifier(DB_SCHEMA))
        cursor.execute(create_gpu_server_trigger)
        print("[OK] Created triggers")
        
        # Commit changes
        conn.commit()
        
        print("\n[OK] Database initialization completed successfully!")
        print(f"[OK] All tables created in schema: {DB_SCHEMA}")
        
        cursor.close()
        conn.close()
        
    except psycopg2.Error as e:
        print(f"[ERROR] Database error: {e}")
        raise
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        raise

def drop_tables():
    """Drop all tables (useful for resetting database)"""
    
    drop_statements = [
        sql.SQL("DROP TABLE IF EXISTS {schema}.users CASCADE;").format(schema=sql.Identifier(DB_SCHEMA)),
        sql.SQL("DROP TABLE IF EXISTS {schema}.roles CASCADE;").format(schema=sql.Identifier(DB_SCHEMA)),
        sql.SQL("DROP TABLE IF EXISTS {schema}.gpu_alert_history CASCADE;").format(schema=sql.Identifier(DB_SCHEMA)),
        sql.SQL("DROP TABLE IF EXISTS {schema}.gpu_server CASCADE;").format(schema=sql.Identifier(DB_SCHEMA)),
        sql.SQL("DROP TABLE IF EXISTS {schema}.pid_metrics CASCADE;").format(schema=sql.Identifier(DB_SCHEMA)),
        sql.SQL("DROP TABLE IF EXISTS {schema}.gpu_metrics CASCADE;").format(schema=sql.Identifier(DB_SCHEMA)),
        sql.SQL("DROP TABLE IF EXISTS {schema}.health_status CASCADE;").format(schema=sql.Identifier(DB_SCHEMA)),
        sql.SQL("DROP TABLE IF EXISTS {schema}.urls CASCADE;").format(schema=sql.Identifier(DB_SCHEMA)),
        sql.SQL("DROP TABLE IF EXISTS {schema}.servers CASCADE;").format(schema=sql.Identifier(DB_SCHEMA)),
        sql.SQL("DROP TABLE IF EXISTS {schema}.projects CASCADE;").format(schema=sql.Identifier(DB_SCHEMA)),
        sql.SQL("DROP FUNCTION IF EXISTS {schema}.update_updated_at_column CASCADE;").format(schema=sql.Identifier(DB_SCHEMA)),
        sql.SQL("DROP SCHEMA IF EXISTS {schema} CASCADE;").format(schema=sql.Identifier(DB_SCHEMA))
    ]
    
    try:
        conn = psycopg2.connect(**DATABASE_CONFIG)
        cursor = conn.cursor()
        
        print(f"Dropping tables and schema {DB_SCHEMA}...")
        for drop_sql in drop_statements:
            cursor.execute(drop_sql)
        
        conn.commit()
        print(f"[OK] All tables and schema {DB_SCHEMA} dropped successfully!")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"[ERROR] Error dropping tables: {e}")
        raise

def reset_database():
    """Reset database by dropping and recreating all tables"""
    print("Resetting database...\n")
    drop_tables()
    print()
    create_tables()

if __name__ == "__main__":
    import sys
    
    print(f"Using schema: {DB_SCHEMA}")
    print(f"Database: {DATABASE_CONFIG['database']}\n")
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "reset":
            reset_database()
        elif sys.argv[1] == "drop":
            drop_tables()
        else:
            print("Usage: python init_db.py [reset|drop]")
    else:
        create_tables()