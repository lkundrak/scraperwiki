from django.db import models
from django.db.models import F
from django.contrib.auth.models import User
from datetime import datetime

from frontend.models import UserProfile

PLAN_PAGE_REQUESTS = {
    'individual':       20000,
    'business':   100000,
    'corporate':      2000000,    
}

# Multiple instances per user are now allowed
class Vault(models.Model):
    
    user = models.ForeignKey(User, related_name='vaults')
    name = models.CharField(max_length=64, blank=True)    
    
    created_at = models.DateTimeField(auto_now_add=True)
    plan = models.CharField(max_length=32, choices=UserProfile.plan_choices)    

    # A list of the members who can access this vault.  This is 
    # distinct from the owner (self.user) of the vault.
    members = models.ManyToManyField(User, related_name='vault_membership')

    def get_code_objects(self):
        from codewiki.models import UserCodeRole, Code                
        return Code.objects.filter(vault=self).exclude(privacy_status='deleted')

    def add_user_rights(self, user ):
        """
        A new user has been added to the vault, make sure they can access all of 
        the code objects.
        """
        from codewiki.models import UserCodeRole, Code        
        role = 'editor'
        if user == self.user:
            role = 'owner'
        for code_object in self.get_code_objects():
            UserCodeRole(code=code_object, user=user,role='editor').save()
            
        
    def remove_user_rights(self, user ):
        """
        A user has been removed from the vault, make sure they can access none of 
        the code objects.
        """
        from codewiki.models import UserCodeRole, Code                
        for code_object in self.get_code_objects():
            UserCodeRole.objects.filter(code=code_object, user=user).all().delete()
        
        
    def update_access_rights(self):
        """
        A code_object has been added to the vault, make sure the UserCodeRoles
        are correct.
        """
        from codewiki.models import UserCodeRole, Code                
        for code_object in self.get_code_objects():
            UserCodeRole.objects.filter(code=code_object).all().delete()
            users = list(self.members.all())
            try:
                users.remove( self.user )
            except ValueError:
                pass
                
            UserCodeRole(code=code_object, user=self.user,role='owner').save()
            for u in users:
                UserCodeRole(code=code_object, user=u,role='editor').save()


    def percentage_this_month(self):
        """
        The percent of pages (using records retrieved and records allowed) fetched this month.
        The value MAY be more than 100%
        """

        pct = float(1.0 * float(self.records_this_month()) / float(self.records_allowed())) * 100;
        if(pct > 0 and pct < 0.1):
            pct = 0.1
        elif(pct >= 0.1 and pct < 10):
            pct = round(pct, 1)
        elif(pct == 0 or pct >= 10):
            pct = int(pct)
        return min(pct, 100)


    def records_this_month(self):
        """
        The number of pages retrieved this month by scrapers in this vault.
        """
        dt = datetime.now()
        try:
            v = self.records.get( year=dt.year, month=dt.month )
            return v.count
        except:
            return 0


    def records_allowed(self):
        """
        The number of pages that this vault is allowed to scrape, across all scrapers
        in each month.
        """
        return PLAN_PAGE_REQUESTS[self.plan]

        
    def __unicode__(self):
        return "%s' %s vault (created on %s)" % (self.user.username, self.plan, self.name)

    class Meta:
        app_label = 'codewiki'
        ordering = ['-name']


class VaultRecord(models.Model):
    """
    Records a counter against a pages scraped. This could be extended to also log
    API calls should that be necessary/
    """
    vault  = models.ForeignKey(Vault, related_name='records')
    year   = models.IntegerField(default=0)    
    month  = models.IntegerField(default=0)        
    count  = models.IntegerField(default=0)        
    
    @staticmethod
    def update(vault, count):
        dt = datetime.now()
        affected = VaultRecord.objects.filter(vault=vault, year=dt.year, month=dt.month ).update(count=F('count') + 1)
        if affected == 0:
            VaultRecord(vault=vault, year=dt.year, month=dt.month, count=count).save()
        
    class Meta:
        app_label = 'codewiki'
        
class Invite(models.Model):
    """
    Represents an invite to a vault
    """

    token = models.CharField(max_length=32)
    vault = models.ForeignKey(Vault)
    email = models.CharField(max_length=200)

    class Meta:
        app_label = 'codewiki'
        
        

        
    
