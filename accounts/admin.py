from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import UserProfile

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    fk_name = 'user'

class CustomUserAdmin(UserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'recipe_count')
    list_select_related = ('profile',)
    
    def recipe_count(self, instance):
        return instance.recipes.count()
    recipe_count.short_description = 'Recipes'
    
    def get_inline_instances(self, request, obj=None):
        if not obj:
            return list()
        return super().get_inline_instances(request, obj)

admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'location', 'join_date', 'recipe_count', 'favorite_count')
    search_fields = ('user__username', 'user__email', 'location')
    readonly_fields = ('join_date',)
    
    def recipe_count(self, obj):
        return obj.recipe_count()
    recipe_count.short_description = 'Recipes'
    
    def favorite_count(self, obj):
        return obj.favorite_count()
    favorite_count.short_description = 'Favorites'