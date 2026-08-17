from django.urls import path
from . import views

urlpatterns = [
    # Recipe CRUD
    path('', views.recipe_list, name='recipe_list'),
    path('create/', views.recipe_create, name='recipe_create'),
    path('<int:pk>/', views.recipe_detail, name='recipe_detail'),
    path('<int:pk>/update/', views.recipe_update, name='recipe_update'),
    path('<int:pk>/delete/', views.recipe_delete, name='recipe_delete'),
    path('my-recipes/', views.my_recipes, name='my_recipes'),
    
    # Interactions
    path('<int:pk>/rate/', views.rate_recipe, name='rate_recipe'),
    path('<int:pk>/like/', views.like_recipe, name='like_recipe'),
    path('<int:pk>/favorite/', views.favorite_recipe, name='favorite_recipe'),
    
    # Print
    path('<int:pk>/print/', views.recipe_print, name='recipe_print'),
    
    # Search
    path('search/suggestions/', views.search_suggestions, name='search_suggestions'),
      path('recipe/<int:pk>/favorite-status/', views.get_favorite_status, name='get_favorite_status'),
]