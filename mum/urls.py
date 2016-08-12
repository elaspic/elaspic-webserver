from django.conf.urls import url
import web_pipeline.views
import web_pipeline.views_json

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()


#urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'mum.views.home', name='home'),
    # url(r'^mum/', include('mum.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    #url(r'^admin/', include(admin.site.urls)),

#)
urlpatterns = []

# Views accessed directly by the user.
urlpatterns += [
    # Input sites.
    url(r'^$', web_pipeline.views.inp, {'p': 'sIn'}),
    url(r'^many/$', web_pipeline.views.inp, {'p': 'mIn'}),

    url(r'^run/$', web_pipeline.views.runPipeline),

    # Results sites.
    url(r'^result/[a-zA-Z0-9]{6,12}/$',
        web_pipeline.views.displayResult),
    url(r'^result/[a-zA-Z0-9]{6,12}/.+\.[A-Za-z]{1}[0-9]+[A-Za-z]{1}/$',
        web_pipeline.views.displaySecondaryResult),

    url(r'^popup/jsmol/$', web_pipeline.views.jsmolpopup),

    # Generic sites.
    url(r'^(help|reference|contact)/$', web_pipeline.views.genericSite),
]

# Views accessed through AJAX calls.
urlpatterns += [
    # Input sites.
    url(r'^json/getprotein/$', web_pipeline.views_json.getProtein),
    url(r'^json/uploadfile/$', web_pipeline.views_json.uploadFile),

    # Results sites.
    url(r'^json/checkjob/$', web_pipeline.views_json.checkIfJobIsReady),
    url(r'^json/rerun/$', web_pipeline.views_json.rerunMut),
    url(r'^json/getdownloads/$', web_pipeline.views_json.prepareDownloadFiles),
    url(r'^getfile/', web_pipeline.views_json.dlFile),

    # Generic.
    url(r'^json/contactmail/$', web_pipeline.views_json.sendContactMail),

    # Cleanup.
    url(r'^cleanup/$', web_pipeline.views_json.cleanup),
]


#urlpatterns += patterns('web_pipeline.views_import',
#
#    url(r'^import/$', 'importBase'),
#
#    url(r'^import/importer/$', 'importer'),
#    url(r'^import/dbupdater/$', 'dbupdater'),
#    url(r'^import/dbreset/$', 'dbreset'),
#)
