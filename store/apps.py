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
                conn.commit()
                conn.close()
            except Exception:
                pass
