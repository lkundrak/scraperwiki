from django.db import models
from django.contrib.auth.models import User


PLAN_TYPES = (
    ('individual', 'Individual'),
    ('corporate', 'Corporate'),    
)

# One instance per user that has a premium account. 
# TODO: Constrain this so each user can only have one.
class Vault(models.Model):
    
    user = models.ForeignKey(User, related_name='vaults')
    name = models.CharField(max_length=64, blank=True)    
    
    created_at = models.DateTimeField(auto_now_add=True)
    plan = models.CharField(max_length=32, choices=PLAN_TYPES)    

    # A list of the members who can access this vault.  This is 
    # distinct from the owner (self.user) of the vault.
    members = models.ManyToManyField(User, related_name='vault_membership')

    def scrapers(self):
        from codewiki.models import UserCodeRole, Scraper                
        return Scraper.objects.filter(vault=self)

    def add_user_rights(self, user ):
        """
        A new user has been added to the vault, make sure they can access all of 
        the scrapers.
        """
        from codewiki.models import UserCodeRole, Scraper        
        role = 'editor'
        if user == self.user:
            role = 'owner'
        for scraper in self.scrapers():
            UserCodeRole(code=scraper, user=user,role='editor').save()
            
        
    def remove_user_rights(self, user ):
        """
        A user has been removed from the vault, make sure they can access none of 
        the scrapers.
        """
        from codewiki.models import UserCodeRole, Scraper                
        for scraper in self.scrapers():
            UserCodeRole.objects.filter(code=scraper, user=user).all().delete()
        
        
    def update_access_rights(self):
        """
        A new scraper has been added to the vault, make sure the UserCodeRoles
        are correct.
        """
        from codewiki.models import UserCodeRole, Scraper                
        for scraper in self.scrapers():
            UserCodeRole.objects.filter(code=scraper).all().delete()
            users = list(self.members.all())
            try:
                users.remove( self.user )
            except ValueError:
                pass
                
            UserCodeRole(code=scraper, user=self.user,role='owner').save()
            for u in users:
                UserCodeRole(code=scraper, user=u,role='editor').save()



    def __unicode__(self):
        return "%s' %s vault (created on %s)" % (self.user.username, self.plan, self.name)

    class Meta:
        app_label = 'codewiki'
        ordering = ['-name']


