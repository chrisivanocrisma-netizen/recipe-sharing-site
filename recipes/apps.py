from django.apps import AppConfig

class RecipesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'recipes'
    
    # Remove the ready() method or keep it empty
    def ready(self):
        pass  # No signals needed for now