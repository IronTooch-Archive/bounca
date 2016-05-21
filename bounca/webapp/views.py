__author__ = "Jeroen Arnoldus"
__copyright__ = "Copyright 2016, Repleo, Amstelveen"
__credits__ = ["Jeroen Arnoldus"]
__license__ = "Apache License"
__version__ = "2.0"
__maintainer__ = "Jeroen Arnoldus"
__email__ = "jeroen@repleo.nl"
__status__ = "Production"

from django.shortcuts import render


import json
from django.http import HttpResponse
from django.views.generic.edit import FormView
from django.utils.encoding import force_text
from django.core.urlresolvers import reverse_lazy
from django.core.exceptions import ObjectDoesNotExist
from .forms import AddRootCAForm

class AddRootCAFormView(FormView):
    template_name = 'bounca/dashboard/forms/add-root-ca.html'
    form_class = AddRootCAForm
    success_url = reverse_lazy('bounca:index') 

from .forms import AddIntermediateCAForm
from ..x509_pki.models import Certificate
from ..x509_pki.models import CertificateTypes

class AddIntermediateCAFormView(FormView):
    template_name = 'bounca/dashboard/forms/add-intermediate-ca.html'
    form_class = AddIntermediateCAForm
    success_url = reverse_lazy('bounca:index') 
    
    def get_initial(self):
        initial = super().get_initial()
        
        if 'parent' not in self.request.GET:
            raise Exception("You should provide the parameter: parent in the url")
        try:
            parent=Certificate.objects.get(pk=self.request.GET['parent'])
        except:
            raise ObjectDoesNotExist("Parent certificate does not exist")
        if parent.type!=CertificateTypes.ROOT and parent.type!=CertificateTypes.INTERMEDIATE:
            raise Exception("Parent certificate type should be root or intermediate")
        initial['parent']=parent.pk;
        initial['dn']={};
        initial['dn']['commonName']=""
        initial['dn']['countryName']=parent.dn.countryName
        initial['dn']['stateOrProvinceName']=parent.dn.stateOrProvinceName
        initial['dn']['localityName']=parent.dn.localityName
        initial['dn']['organizationName']=parent.dn.organizationName
        initial['dn']['organizationalUnitName']=parent.dn.organizationalUnitName
        initial['dn']['emailAddress']=parent.dn.emailAddress
       
        return initial
    
from .forms import AddServerCertificateForm


class AddServerCertificateFormView(FormView):
    template_name = 'bounca/dashboard/forms/add-server-cert.html'
    form_class = AddServerCertificateForm
    success_url = reverse_lazy('bounca:index') 
    
    def get_initial(self):
        initial = super().get_initial()
        
        if 'parent' not in self.request.GET:
            raise Exception("You should provide the parameter: parent in the url")
        try:
            parent=Certificate.objects.get(pk=self.request.GET['parent'])
        except:
            raise ObjectDoesNotExist("Parent certificate does not exist")
#TODO webapp cannot handle the Exception
#        if parent.type!=CertificateTypes.INTERMEDIATE:
#            raise Exception("Parent certificate type should be intermediate")
        initial['parent']=parent.pk;
        initial['dn']={};
        initial['dn']['commonName']=""
        initial['dn']['countryName']=parent.dn.countryName
        initial['dn']['stateOrProvinceName']=parent.dn.stateOrProvinceName
        initial['dn']['localityName']=parent.dn.localityName
        initial['dn']['organizationName']=parent.dn.organizationName
        initial['dn']['organizationalUnitName']=parent.dn.organizationalUnitName
        initial['dn']['emailAddress']=parent.dn.emailAddress
       
        return initial
    
from .forms import AddClientCertificateForm


class AddClientCertificateFormView(FormView):
    template_name = 'bounca/dashboard/forms/add-client-cert.html'
    form_class = AddClientCertificateForm
    success_url = reverse_lazy('bounca:index') 
    
    def get_initial(self):
        initial = super().get_initial()
        
        if 'parent' not in self.request.GET:
            raise Exception("You should provide the parameter: parent in the url")
        try:
            parent=Certificate.objects.get(pk=self.request.GET['parent'])
        except:
            raise ObjectDoesNotExist("Parent certificate does not exist")
#TODO webapp cannot handle the Exception
#        if parent.type!=CertificateTypes.INTERMEDIATE:
#            raise Exception("Parent certificate type should be intermediate")
        initial['parent']=parent.pk;
        initial['dn']={};
        initial['dn']['commonName']=""
        initial['dn']['countryName']=parent.dn.countryName
        initial['dn']['stateOrProvinceName']=parent.dn.stateOrProvinceName
        initial['dn']['localityName']=parent.dn.localityName
        initial['dn']['organizationName']=parent.dn.organizationName
        initial['dn']['organizationalUnitName']=parent.dn.organizationalUnitName
        initial['dn']['emailAddress']=parent.dn.emailAddress
       
        return initial
    
from .forms import CertificateRevokeForm
class CertificateRevokeFormView(FormView):
    template_name = 'bounca/dashboard/forms/revoke-cert.html'
    form_class = CertificateRevokeForm
    success_url = reverse_lazy('bounca:index') 
    
from .forms import CertificateCRLForm
class CertificateCRLFormView(FormView):
    template_name = 'bounca/dashboard/forms/crl-file.html'
    form_class = CertificateCRLForm
    success_url = reverse_lazy('bounca:index') 

from django_ical.views import ICalFeed
from ..x509_pki.models import Certificate

class CertificateExpireCalendarView(ICalFeed):
    product_id = '-//bounca.org//BounCA Certificate Expiration Dates//EN'
    timezone = 'GMT'
    file_name = "certificates.ics"

    def get_object(self, request):
        return request.user


    def items(self,obj):
        return Certificate.objects.filter(owner=obj.id).order_by('-expires_at')

    def item_title(self, item):
        return "Certificate " + str(item) + " expires"

    def item_description(self, item):
        issued_by = ""
        if item.parent:
            issued_by = "issued by: " + item.parent.dn.commonName + "\n"
        subjectAltNames =""
        if item.dn.subjectAltNames:
            subjectAltNames = "with subject alternatives:\n"
            for alt_name in item.dn.subjectAltNames:
                subjectAltNames = subjectAltNames + alt_name + "\n"
        return "Certificate: \n" + \
            item.dn.commonName + "\n"+ \
            subjectAltNames + \
            issued_by + \
            "with name: " + item.shortname + "\n" + \
            "is expired"
            

    def item_start_datetime(self, item):
        if item.revoked:
            return item.revoked_at
        else:
            return item.expires_at
    
    def item_created(self, item):
        return item.created_at
    
    def item_link(self, item):
        return "https://www.bounca.org"


    def item_guid(self, item):
        return item.id
    
