from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Avg, Count
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import Recipe, Ingredient, Step, Tag, Rating, Like, Favorite
from .forms import RecipeForm, RatingForm
import json

def recipe_list(request):
    recipes = Recipe.objects.all().select_related('author').prefetch_related('tags')
    
    # Search
    query = request.GET.get('q')
    if query:
        recipes = recipes.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(ingredients__name__icontains=query)
        ).distinct()
    
    # Filter by category
    category = request.GET.get('category')
    if category:
        recipes = recipes.filter(category=category)
    
    # Filter by difficulty
    difficulty = request.GET.get('difficulty')
    if difficulty:
        recipes = recipes.filter(difficulty=difficulty)
    
    # Filter by prep time
    prep_time = request.GET.get('prep_time')
    if prep_time:
        if prep_time == 'under_30':
            recipes = recipes.filter(prep_time__lte=30)
        elif prep_time == '30_60':
            recipes = recipes.filter(prep_time__gte=30, prep_time__lte=60)
        elif prep_time == 'over_60':
            recipes = recipes.filter(prep_time__gt=60)
    
    # Filter by tags
    tag_ids = request.GET.getlist('tags')
    if tag_ids:
        recipes = recipes.filter(tags__id__in=tag_ids).distinct()
    
    # Sort
    sort_by = request.GET.get('sort', '-created_at')
    if sort_by == 'rating':
        recipes = recipes.annotate(avg_rating=Avg('ratings__rating')).order_by('-avg_rating')
    elif sort_by == 'likes':
        recipes = recipes.annotate(like_count=Count('likes')).order_by('-like_count')
    else:
        recipes = recipes.order_by(sort_by)
    
    # Calculate average rating for each recipe
    recipes = recipes.annotate(average_rating=Avg('ratings__rating'))
    
    # Pagination
    paginator = Paginator(recipes, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # ✅ ✅ ✅ ADD THIS: SET is_favorite ATTRIBUTE FOR EACH RECIPE
    if request.user.is_authenticated:
        # Get all favorite recipe IDs for the current user
        favorite_ids = Favorite.objects.filter(
            user=request.user, 
            recipe__in=page_obj.object_list
        ).values_list('recipe_id', flat=True)
        
        # Convert to set for faster lookup
        favorite_set = set(favorite_ids)
        
        # Add is_favorite attribute to each recipe in the page
        for recipe in page_obj.object_list:
            recipe.is_favorite = recipe.id in favorite_set
    else:
        # For non-authenticated users, set is_favorite to False
        for recipe in page_obj.object_list:
            recipe.is_favorite = False
    
    tags = Tag.objects.all()
    
    context = {
        'page_obj': page_obj,
        'recipes': page_obj.object_list,  # ✅ Now has is_favorite attribute
        'tags': tags,
        'query': query,
        'category': category,
        'difficulty': difficulty,
        'prep_time': prep_time,
        'sort_by': sort_by,
    }
    return render(request, 'recipes/recipe_list.html', context)

def recipe_detail(request, pk):
    recipe = get_object_or_404(Recipe.objects.select_related('author'), pk=pk)
    ingredients = recipe.ingredients.all()
    steps = recipe.steps.all().order_by('step_number')
    ratings = recipe.ratings.all().select_related('user')
    
    # Check if user has rated/liked/favorited
    user_rating = None
    user_like = None
    is_favorite = False
    
    if request.user.is_authenticated:
        user_rating = recipe.ratings.filter(user=request.user).first()
        user_like = recipe.likes.filter(user=request.user).first()
        is_favorite = Favorite.objects.filter(user=request.user, recipe=recipe).exists()
    
    rating_form = RatingForm()
    
    # Calculate average rating
    average_rating = recipe.ratings.aggregate(Avg('rating'))['rating__avg'] or 0
    
    # Get likes count
    likes_count = recipe.likes.filter(is_like=True).count()
    
    context = {
        'recipe': recipe,
        'ingredients': ingredients,
        'steps': steps,
        'ratings': ratings,
        'user_rating': user_rating,
        'user_like': user_like,
        'is_favorite': is_favorite,
        'rating_form': rating_form,
        'average_rating': average_rating,
        'likes_count': likes_count,
    }
    return render(request, 'recipes/recipe_detail.html', context)

@login_required
def recipe_create(request):
    if request.method == 'POST':
        # Handle photo upload
        photo = request.FILES.get('photo')
        
        # Create recipe with basic info
        recipe = Recipe(
            title=request.POST.get('title'),
            description=request.POST.get('description'),
            prep_time=request.POST.get('prep_time', 15),
            cook_time=request.POST.get('cook_time', 30),
            servings=request.POST.get('servings', 4),
            difficulty=request.POST.get('difficulty', 'medium'),
            category=request.POST.get('category', 'dinner'),
            author=request.user
        )
        
        if photo:
            recipe.photo = photo
        
        try:
            recipe.save()
            
            # IMPORTANT FIX: Get ingredients correctly from template
            quantities = request.POST.getlist('quantity[]')
            units = request.POST.getlist('unit[]')
            names = request.POST.getlist('name[]')
            
            # Save ingredients (3 fields: quantity, unit, name)
            for i, (quantity, unit, name) in enumerate(zip(quantities, units, names)):
                if name.strip():  # Only save if ingredient name is not empty
                    Ingredient.objects.create(
                        recipe=recipe,
                        quantity=quantity.strip(),
                        unit=unit.strip(),
                        name=name.strip()
                    )
            
            # IMPORTANT FIX: Get steps correctly from template
            steps = request.POST.getlist('steps[]')
            for i, step_text in enumerate(steps):
                if step_text.strip():  # Only save non-empty steps
                    Step.objects.create(
                        recipe=recipe,
                        instruction=step_text.strip(),
                        step_number=i + 1
                    )
            
            messages.success(request, 'Recipe created successfully!')
            return redirect('recipe_detail', pk=recipe.pk)
            
        except Exception as e:
            messages.error(request, f'Error creating recipe: {str(e)}')
            # Re-render form with existing data
            context = {
                'form': {
                    'title': request.POST.get('title', ''),
                    'description': request.POST.get('description', ''),
                    'prep_time': request.POST.get('prep_time', 15),
                    'cook_time': request.POST.get('cook_time', 30),
                    'servings': request.POST.get('servings', 4),
                    'difficulty': request.POST.get('difficulty', 'medium'),
                    'category': request.POST.get('category', 'dinner'),
                },
                'title': 'Create Recipe',
            }
            return render(request, 'recipes/recipe_form.html', context)
    
    # GET request - show empty form
    context = {
        'title': 'Create Recipe',
        'form': {
            'prep_time': 15,
            'cook_time': 30,
            'servings': 4,
            'difficulty': 'medium',
            'category': 'dinner',
        }
    }
    return render(request, 'recipes/recipe_form.html', context)

@login_required
def recipe_update(request, pk):
    recipe = get_object_or_404(Recipe, pk=pk, author=request.user)
    
    if request.method == 'POST':
        # Handle photo upload
        photo = request.FILES.get('photo')
        
        # Update recipe basic info
        recipe.title = request.POST.get('title')
        recipe.description = request.POST.get('description')
        recipe.prep_time = request.POST.get('prep_time')
        recipe.cook_time = request.POST.get('cook_time')
        recipe.servings = request.POST.get('servings')
        recipe.difficulty = request.POST.get('difficulty')
        recipe.category = request.POST.get('category')
        
        if photo:
            recipe.photo = photo
        
        try:
            recipe.save()
            
            # Get existing ingredients
            existing_ingredients = list(recipe.ingredients.all())
            existing_steps = list(recipe.steps.all())
            
            # Get new data from form
            quantities = request.POST.getlist('quantity[]')
            units = request.POST.getlist('unit[]')
            names = request.POST.getlist('name[]')
            steps = request.POST.getlist('steps[]')
            
            # UPDATE INGREDIENTS (not delete all)
            for i, (quantity, unit, name) in enumerate(zip(quantities, units, names)):
                if name.strip():  # Only process if ingredient name is not empty
                    if i < len(existing_ingredients):
                        # Update existing ingredient
                        existing_ingredients[i].quantity = quantity.strip()
                        existing_ingredients[i].unit = unit.strip()
                        existing_ingredients[i].name = name.strip()
                        existing_ingredients[i].save()
                    else:
                        # Create new ingredient if more than existing
                        Ingredient.objects.create(
                            recipe=recipe,
                            quantity=quantity.strip(),
                            unit=unit.strip(),
                            name=name.strip()
                        )
            
            # If there are fewer ingredients in form than existing, delete extras
            if len(names) < len(existing_ingredients):
                for i in range(len(names), len(existing_ingredients)):
                    existing_ingredients[i].delete()
            
            # UPDATE STEPS (not delete all)
            for i, step_text in enumerate(steps):
                if step_text.strip():  # Only process if step is not empty
                    if i < len(existing_steps):
                        # Update existing step
                        existing_steps[i].instruction = step_text.strip()
                        existing_steps[i].step_number = i + 1
                        existing_steps[i].save()
                    else:
                        # Create new step if more than existing
                        Step.objects.create(
                            recipe=recipe,
                            instruction=step_text.strip(),
                            step_number=i + 1
                        )
            
            # If there are fewer steps in form than existing, delete extras
            if len(steps) < len(existing_steps):
                for i in range(len(steps), len(existing_steps)):
                    existing_steps[i].delete()
            
            messages.success(request, 'Recipe updated successfully!')
            return redirect('recipe_detail', pk=recipe.pk)
            
        except Exception as e:
            messages.error(request, f'Error updating recipe: {str(e)}')
            # For debugging
            print(f"Error: {e}")
            # Return with POST data to keep form inputs
            return render(request, 'recipes/recipe_form.html', {
                'recipe': recipe,
                'title': 'Update Recipe',
                'form': request.POST,
                'ingredients': recipe.ingredients.all(),
                'steps': recipe.steps.all().order_by('step_number'),
            })
    
    # GET request - show form with existing data
    ingredients = recipe.ingredients.all()
    steps = recipe.steps.all().order_by('step_number')
    
    # Create a form-like dictionary with recipe data
    form_data = {
        'title': recipe.title,
        'description': recipe.description,
        'prep_time': recipe.prep_time,
        'cook_time': recipe.cook_time,
        'servings': recipe.servings,
        'difficulty': recipe.difficulty,
        'category': recipe.category,
    }
    
    context = {
        'recipe': recipe,
        'title': 'Update Recipe',
        'form': form_data,
        'ingredients': ingredients,
        'steps': steps,
    }
    return render(request, 'recipes/recipe_form.html', context)

@login_required
def recipe_delete(request, pk):
    recipe = get_object_or_404(Recipe, pk=pk, author=request.user)
    
    if request.method == 'POST':
        recipe.delete()
        messages.success(request, 'Recipe deleted successfully!')
        return redirect('my_recipes')
    
    return render(request, 'recipes/recipe_delete.html', {'recipe': recipe})

@login_required
def my_recipes(request):
    recipes = Recipe.objects.filter(author=request.user).order_by('-created_at')
    context = {
        'recipes': recipes,
    }
    return render(request, 'recipes/my_recipes.html', context)

@login_required
@require_POST
def rate_recipe(request, pk):
    recipe = get_object_or_404(Recipe, pk=pk)
    rating_value = int(request.POST.get('rating', 0))
    comment = request.POST.get('comment', '')
    
    if 1 <= rating_value <= 5:
        rating, created = Rating.objects.update_or_create(
            recipe=recipe,
            user=request.user,
            defaults={'rating': rating_value, 'comment': comment}
        )
        
        if created:
            messages.success(request, 'Thank you for your rating!')
        else:
            messages.info(request, 'Your rating has been updated!')
    
    return redirect('recipe_detail', pk=pk)

@login_required
@require_POST
def like_recipe(request, pk):
    recipe = get_object_or_404(Recipe, pk=pk)
    like, created = Like.objects.get_or_create(
        recipe=recipe,
        user=request.user,
        defaults={'is_like': True}
    )
    
    if not created:
        if like.is_like:
            like.delete()
            liked = False
        else:
            like.is_like = True
            like.save()
            liked = True
    else:
        liked = True
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'liked': liked,
            'likes_count': recipe.likes.filter(is_like=True).count()
        })
    
    return redirect('recipe_detail', pk=pk)

@login_required
@require_POST
def favorite_recipe(request, pk):
    recipe = get_object_or_404(Recipe, pk=pk)
    
    try:
        favorite, created = Favorite.objects.get_or_create(
            user=request.user,
            recipe=recipe
        )
        
        if not created:
            # If already exists, remove it (unfavorite)
            favorite.delete()
            is_favorite = False
            message = "Removed from favorites"
        else:
            is_favorite = True
            message = "Added to favorites!"
        
        # Get favorite count for this recipe
        favorite_count = Favorite.objects.filter(recipe=recipe).count()
        
        # Check if it's an AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'is_favorite': is_favorite,
                'favorite_count': favorite_count,
                'message': message,
                'recipe_id': recipe.id,
            })
        
        # For non-AJAX requests
        messages.success(request, message)
        return redirect(request.META.get('HTTP_REFERER', 'recipe_list'))
        
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
        messages.error(request, "Error updating favorite")
        return redirect(request.META.get('HTTP_REFERER', 'recipe_list'))

def recipe_print(request, pk):
    recipe = get_object_or_404(Recipe, pk=pk)
    ingredients = recipe.ingredients.all()
    steps = recipe.steps.all().order_by('step_number')
    
    context = {
        'recipe': recipe,
        'ingredients': ingredients,
        'steps': steps,
    }
    return render(request, 'recipes/recipe_print.html', context)

def search_suggestions(request):
    query = request.GET.get('q', '')
    if query:
        recipes = Recipe.objects.filter(title__icontains=query)[:5]
        suggestions = [recipe.title for recipe in recipes]
        return JsonResponse(suggestions, safe=False)
    return JsonResponse([], safe=False)

def featured_recipes(request):
    featured = Recipe.objects.filter(is_featured=True)[:8]
    return render(request, 'recipes/featured_recipes.html', {'featured_recipes': featured})

def recipes_by_category(request, category):
    recipes = Recipe.objects.filter(category=category).order_by('-created_at')
    
    # Add is_favorite for authenticated users
    if request.user.is_authenticated:
        favorite_ids = Favorite.objects.filter(
            user=request.user, 
            recipe__in=recipes
        ).values_list('recipe_id', flat=True)
        favorite_set = set(favorite_ids)
        
        for recipe in recipes:
            recipe.is_favorite = recipe.id in favorite_set
    else:
        for recipe in recipes:
            recipe.is_favorite = False
    
    context = {
        'recipes': recipes,
        'category': category,
        'category_display': dict(Recipe.CATEGORY_CHOICES).get(category, category)
    }
    return render(request, 'recipes/recipes_by_category.html', context)

def popular_recipes(request):
    recipes = Recipe.objects.annotate(
        like_count=Count('likes'),
        rating_avg=Avg('ratings__rating')
    ).order_by('-like_count', '-rating_avg')[:10]
    
    # Add is_favorite for authenticated users
    if request.user.is_authenticated:
        favorite_ids = Favorite.objects.filter(
            user=request.user, 
            recipe__in=recipes
        ).values_list('recipe_id', flat=True)
        favorite_set = set(favorite_ids)
        
        for recipe in recipes:
            recipe.is_favorite = recipe.id in favorite_set
    else:
        for recipe in recipes:
            recipe.is_favorite = False
    
    return render(request, 'recipes/popular_recipes.html', {'recipes': recipes})

@login_required
def my_favorites(request):
    # Get user's favorite recipes with related data
    favorites = Favorite.objects.filter(user=request.user).select_related('recipe', 'recipe__author')
    
    # Get the actual recipe objects
    favorite_recipes = [fav.recipe for fav in favorites]
    
    # Add is_favorite attribute (always True for favorites page)
    for recipe in favorite_recipes:
        recipe.is_favorite = True
    
    # Pagination
    paginator = Paginator(favorite_recipes, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'favorites': favorites,
        'page_obj': page_obj,
        'favorite_recipes': page_obj.object_list,
        'favorite_count': len(favorite_recipes),
    }
    return render(request, 'recipes/favorites.html', context)

# ADDITIONAL VIEWS FOR AJAX FUNCTIONALITY

@login_required
def toggle_favorite_ajax(request, pk):
    """AJAX-only view for toggling favorites"""
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': False, 'error': 'Not an AJAX request'})
    
    recipe = get_object_or_404(Recipe, pk=pk)
    
    try:
        favorite, created = Favorite.objects.get_or_create(
            user=request.user,
            recipe=recipe
        )
        
        if not created:
            favorite.delete()
            is_favorite = False
            message = "Removed from favorites"
        else:
            is_favorite = True
            message = "Added to favorites!"
        
        favorite_count = Favorite.objects.filter(recipe=recipe).count()
        
        return JsonResponse({
            'success': True,
            'is_favorite': is_favorite,
            'favorite_count': favorite_count,
            'message': message,
            'recipe_id': recipe.id,
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

def get_favorite_status(request, pk):
    """Check if a recipe is favorited by current user"""
    if not request.user.is_authenticated:
        return JsonResponse({'is_favorite': False})
    
    recipe = get_object_or_404(Recipe, pk=pk)
    is_favorite = Favorite.objects.filter(user=request.user, recipe=recipe).exists()
    
    return JsonResponse({
        'is_favorite': is_favorite,
        'recipe_id': recipe.id,
    })