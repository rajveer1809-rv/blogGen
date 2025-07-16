from django.urls import path
from .views import blog_generator

urlpatterns = [
    path('', blog_generator, name='blog_generator'),
] 