from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from .forms import UserRegisterForm, UserLoginForm, UserUpdateForm, ProfileUpdateForm
from recipes.models import Recipe, Favorite
from django.contrib.auth.forms import PasswordChangeForm

def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}! You can now login.')
            return redirect('login')
    else:
        form = UserRegisterForm()
    
    return render(request, 'accounts/register.html', {'form': form})

def user_login(request):
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = UserLoginForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            
            # Redirect to next page if exists
            next_page = request.GET.get('next')
            if next_page:
                return redirect(next_page)
            return redirect('home')
    else:
        form = UserLoginForm()
    
    return render(request, 'accounts/login.html', {'form': form})

@login_required
def user_logout(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('home')

@login_required
def profile(request):
    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)
        
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Your profile has been updated!')
            return redirect('profile')
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileUpdateForm(instance=request.user.profile)
    
    # Get user's recipes and favorites
    user_recipes = Recipe.objects.filter(author=request.user).order_by('-created_at')[:5]
    user_favorites = Favorite.objects.filter(user=request.user).select_related('recipe')[:5]
    
    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'user_recipes': user_recipes,
        'user_favorites': user_favorites,
    }
    return render(request, 'accounts/profile.html', context)

@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password was successfully updated!')
            return redirect('profile')
    else:
        form = PasswordChangeForm(request.user)
    
    return render(request, 'accounts/change_password.html', {'form': form})

def user_profile_public(request, username):
    user = get_object_or_404(User, username=username)
    recipes = Recipe.objects.filter(author=user).order_by('-created_at')
    
    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(recipes, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'profile_user': user,
        'recipes': page_obj.object_list,
        'page_obj': page_obj,
        'recipe_count': recipes.count(),
    }
    return render(request, 'accounts/user_profile_public.html', context)

from django.http import JsonResponse
from recipes.models import Recipe, Favorite

@login_required
def toggle_favorite(request, recipe_id):
    recipe = get_object_or_404(Recipe, id=recipe_id)
    
    if request.method == 'POST':
        # Toggle favorite status
        favorite, created = Favorite.objects.get_or_create(
            user=request.user,
            recipe=recipe
        )
        
        if not created:
            # If already exists, remove it (unfavorite)
            favorite.delete()
            is_favorite = False
        else:
            is_favorite = True
        
        # Check if it's AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'is_favorite': is_favorite,
                'favorite_count': recipe.favorites.count(),  # or recipe.favorite_set.count()
                'recipe_id': recipe_id,
            })
        
        # For non-AJAX requests
        return redirect(request.META.get('HTTP_REFERER', 'recipe_list'))
    
    return redirect('recipe_list')

@login_required
def favorites_list(request):
    # Get all favorite recipes for current user
    favorites = Favorite.objects.filter(user=request.user).select_related('recipe')
    
    # Get the actual recipe objects
    favorite_recipes = [fav.recipe for fav in favorites]
    
    # You can add pagination if needed
    from django.core.paginator import Paginator
    paginator = Paginator(favorite_recipes, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'favorites': favorites,  # or 'recipes': favorite_recipes
        'page_obj': page_obj,
        'favorite_count': len(favorite_recipes),
    }
    return render(request, 'recipes/favorites_list.html', context)