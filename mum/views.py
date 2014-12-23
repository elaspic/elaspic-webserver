from django.shortcuts import render



def home(request):
    context = {
        'current': 'home',
    }
    return render(request, 'home.html', context)


'''
def query(request, queryID):
    queryContext = {'content': queryID}
    queryContext.update(context)
    return render(request, 'query.html', queryContext)
'''