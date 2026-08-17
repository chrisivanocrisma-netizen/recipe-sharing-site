from django.contrib import admin
from .models import Recipe, Ingredient, Step, Tag, Rating, Like, Favorite

class IngredientInline(admin.TabularInline):
    model = Ingredient
    extra = 1

class StepInline(admin.TabularInline):
    model = Step
    extra = 1

class RatingInline(admin.TabularInline):
    model = Rating
    extra = 0

@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'category', 'difficulty', 'prep_time', 'cook_time', 'created_at', 'is_featured')
    list_filter = ('category', 'difficulty', 'created_at', 'is_featured', 'tags')
    search_fields = ('title', 'description', 'author__username')
    list_editable = ('is_featured',)
    filter_horizontal = ('tags',)
    inlines = [IngredientInline, StepInline]
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Basic Info', {
            'fields': ('title', 'description', 'author', 'photo', 'tags')
        }),
        ('Details', {
            'fields': ('prep_time', 'cook_time', 'servings', 'difficulty', 'category')
        }),
        ('Status', {
            'fields': ('is_featured', 'created_at', 'updated_at')
        }),
    )

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'color', 'recipe_count')
    search_fields = ('name',)
    
    def recipe_count(self, obj):
        return obj.recipe_set.count()
    recipe_count.short_description = 'Number of Recipes'

@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'user', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('recipe__title', 'user__username', 'comment')

@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'user', 'is_like', 'created_at')
    list_filter = ('is_like', 'created_at')
    search_fields = ('recipe__title', 'user__username')

@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'recipe__title')

# Register remaining models
admin.site.register(Ingredient)
admin.site.register(Step)