# app/apps.py
from django.apps import AppConfig

class AppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "app"
    verbose_name = "Hospital Management System"
    
    def ready(self):
        """
        Initialize app when Django starts
        """
        # Import signals here to ensure they are connected
        try:
            import app.signals
        except ImportError:
            pass
        
        # Any other initialization code can go here
        self.validate_settings()
    
    def validate_settings(self):
        """
        Validate required settings for the app
        """
        from django.conf import settings
        
        # Check for required settings
        required_settings = [
            'GROQ_API_KEY',
            'GROQ_MODEL',
        ]
        
        missing_settings = []
        for setting in required_settings:
            if not hasattr(settings, setting) or not getattr(settings, setting):
                missing_settings.append(setting)
        
        if missing_settings:
            import warnings
            warnings.warn(
                f"Missing required settings: {', '.join(missing_settings)}. "
                f"Some features may not work properly.",
                RuntimeWarning
            )
