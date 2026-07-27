from django.http import HttpResponse


def index(request):
    return HttpResponse("Paper job app is ready.")
