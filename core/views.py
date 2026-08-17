from django.shortcuts import render
from recipes.models import Recipe, Tag
from django.db.models import Count
import random

def home(request):
    # Featured recipes
    featured_recipes = Recipe.objects.filter(is_featured=True)[:4]
    
    # Latest recipes
    latest_recipes = Recipe.objects.all().order_by('-created_at')[:8]
    
    # Popular recipes (by likes)
    popular_recipes = Recipe.objects.annotate(
        like_count=Count('likes')
    ).order_by('-like_count')[:4]
    
    # Random recipe of the day
    all_recipes = list(Recipe.objects.all())
    recipe_of_day = random.choice(all_recipes) if all_recipes else None
    
    # Get categories for filter
    categories = Recipe.objects.values_list('category', flat=True).distinct()
    
    context = {
        'featured_recipes': featured_recipes,
        'latest_recipes': latest_recipes,
        'popular_recipes': popular_recipes,
        'recipe_of_day': recipe_of_day,
        'categories': categories,
    }
    return render(request, 'home.html', context)

def about(request):
    return render(request, 'core/about.html')

def contact(request):
    return render(request, 'core/contact.html')

def categories(request):
    categories_data = []
    for category_code, category_name in Recipe.CATEGORY_CHOICES:
        count = Recipe.objects.filter(category=category_code).count()
        categories_data.append({
            'code': category_code,
            'name': category_name,
            'count': count
        })
    
    # Get tags with count
    tags = Tag.objects.annotate(recipe_count=Count('recipe')).order_by('-recipe_count')
    
    context = {
        'categories': categories_data,
        'tags': tags,
    }
    return render(request, 'core/categories.html', context)

