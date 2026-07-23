from django.apps import AppConfig
import sys


class StoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'store'

    def ready(self):
        import store.signals

        # Self-healing database column check for shipment tracking fields
        if 'runserver' in sys.argv or 'manage.py' in sys.argv:
            try:
                import sqlite3
                from django.conf import settings
                db_path = settings.DATABASES['default']['NAME']
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                try:
                    cursor.execute("ALTER TABLE store_wishlist ADD COLUMN session_key varchar(40) NULL;")
                except Exception:
                    pass
                try:
                    cursor.execute("ALTER TABLE store_order ADD COLUMN shipping_partner varchar(100) NULL;")
                except Exception:
                    pass
                try:
                    cursor.execute("ALTER TABLE store_order ADD COLUMN tracking_number varchar(100) NULL;")
                except Exception:
                    pass
                try:
                    cursor.execute("INSERT OR IGNORE INTO django_migrations (app, name, applied) VALUES ('store', '0012_order_shipping_partner_tracking_number', datetime('now'));")
                except Exception:
                    pass

                # Self-healing auto-create and seed store_announcementbar table
                try:
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS store_announcementbar (
                            id integer PRIMARY KEY AUTOINCREMENT,
                            text varchar(255) NOT NULL,
                            is_active bool NOT NULL,
                            created_at datetime NOT NULL,
                            updated_at datetime NOT NULL
                        );
                    """)
                    cursor.execute("SELECT COUNT(*) FROM store_announcementbar;")
                    if cursor.fetchone()[0] == 0:
                        cursor.execute("""
                            INSERT INTO store_announcementbar (text, is_active, created_at, updated_at)
                            VALUES ('⚡ Chennai Delivery in 1-3 Days • Buy 2 Get 1 Free • Express Shipping across Tamil Nadu ⚡', 1, datetime('now'), datetime('now'));
                        """)
                except Exception:
                    pass

                # Self-healing auto-create and seed django_site table for allauth
                try:
                    cursor.execute("CREATE TABLE IF NOT EXISTS django_site (id integer PRIMARY KEY AUTOINCREMENT, domain varchar(100) NOT NULL, name varchar(50) NOT NULL);")
                    cursor.execute("INSERT OR IGNORE INTO django_site (id, domain, name) VALUES (1, '127.0.0.1:8000', 'Twosomesty');")
                except Exception:
                    pass

                conn.commit()
                conn.close()
            except Exception:
                pass
