from django.conf.urls import patterns, url

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'mum.views.home', name='home'),
    # url(r'^mum/', include('mum.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    #url(r'^admin/', include(admin.site.urls)),

)

# Views accessed directly by the user.
urlpatterns += patterns('web_pipeline.views',

    # Input sites.
    url(r'^$', 'inp', {'p': 'sIn'}),
    url(r'^many/$', 'inp', {'p': 'mIn'}),

    url(r'^run/$', 'runPipeline'),

    # Results sites.
    url(r'^result/[a-zA-Z0-9]{6}/$', 'displayResult'),
    url(r'^result/[a-zA-Z0-9]{6}/.+\.[A-Za-z]{1}[0-9]+[A-Za-z]{1}/$', 'displaySecondaryResult'),

    url(r'^popup/jsmol/$', 'jsmolpopup'),

    # Generic sites.
    url(r'^(help|reference|contact)/$', 'genericSite'),
    

)

# Views accessed through AJAX calls.
urlpatterns += patterns('web_pipeline.views_json',

    # Input sites.
    url(r'^json/getprotein/$', 'getProtein'),
    url(r'^json/uploadfile/$', 'uploadFile'),

    # Results sites.
    url(r'^json/checkjob/$', 'checkIfJobIsReady'),
    url(r'^json/rerun/$', 'rerunMut'),
    url(r'^json/getdownloads/$', 'prepareDownloadFiles'),
    url(r'^getfile/', 'dlFile'),

    # Generic.
    url(r'^json/contactmail/$', 'sendContactMail'),

    # Cleanup.
    url(r'^cleanup/$', 'cleanup'),
)


#urlpatterns += patterns('web_pipeline.views_import',
#
#    url(r'^import/$', 'importBase'),
#
#    url(r'^import/importer/$', 'importer'),
#    url(r'^import/dbupdater/$', 'dbupdater'),
#    url(r'^import/dbreset/$', 'dbreset'),
#)
