from django.db import models
from acecommerce.utils import gf
from datetime import date
from django.contrib.contenttypes.models import ContentType

class Category(models.Model):
    """ 
    A category to which products may belong.
    """
    name = models.CharField(blank=True, max_length=100)
    slug = models.SlugField()
    
    def __unicode__(self):
        return self.name

class AvailabilityType(models.Model):
    """ 
    A type of product availability.
    """
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=100)
    
    def __unicode__(self):
        return self.name

class Availability(models.Model):
    """ 
    Availability for a product.
    """
    availability_type = models.ForeignKey(AvailabilityType)
    
    @property
    def helper(self):
        """ 
        Gets the helper object.
        """
        return gf(self.availability_type.code).objects.get(availability=self)
    
    def available(self):
        """ 
        Returns True if available, False otherwise.
        """
        return self.helper.available()
    
    def record_purchase(self,quantity=1):
        """ 
        Records the purchase of the item, in case it affects availability.
        Raises QuantityExceedsAvailable if the requested quantity is
        more than what's available.
        """
        self.helper.record_purchase(quantity=quantity)

class QuantityExceedsAvailable(Exception):
    """ 
    Indicates the requested quantity exceeds what's available.
    """

class AvailabilityMixin(object):
    """ 
    Implements no-op methods.
    """
    def quantity_available(self,quantity=1):
        """ 
        Is the requested quantity available.?
        """
        return True
    
    def record_purchase(self,quantity=1):
        """ 
        No-op.
        """
        pass # No-op

class BooleanAvailability(models.Model,AvailabilityMixin):
    """ 
    Product is either available or it isn't.
    """
    availability = models.ForeignKey(Availability,unique=True)
    is_available = models.BooleanField(default=True)
    
    def available(self):
        """ 
        Returns True if is_available flag set to true, false otherwise.
        """
        return self.is_available

class CountdownAvailability(models.Model):
    """ 
    Each purchase reduces availability by 1 until the product goes out of stock.
    """
    availability = models.ForeignKey(Availability,unique=True)
    num_products = models.IntegerField(default=0)
    
    def available(self):
        """ 
        Returns True if num_products > 0.
        """
        return True if self.num_products > 0 else False
    
    def quantity_available(self,quantity=1):
        """ 
        Returns True if the requested quantity is less or equal to
        the number of products.
        """
        return True if quantity <= self.num_products else False
    
    def record_purchase(self,quantity=1):
        """ 
        Decrements the num_products.
        """
        if quantity > self.num_products:
            raise QuantityExceedsAvailable()
        
        self.num_products = max(self.num_products - quantity,0)
        self.save()

class DateRangeAvailability(models.Model,AvailabilityMixin):
    """ 
    Product is available between specified date ranges.
    """
    start_date = models.DateField(null=True)
    end_date = models.DateField(null=True)
    
    def available(self):
        """ 
        Available if the current day is after a non-null start_date
        and before a non-null end date.
        """
        today = date.today()
        if self.start_date and today < self.start_date:
            return False # too soon
        elif self.end_date and today > self.end_date:
            return False # too late
        else:
            return True

class ProductType(models.Model):
    """ 
    A type of product.
    """
    name = models.CharField(unique=True, max_length=100)
    content_type = models.ForeignKey(ContentType)
    configurable = models.BooleanField(default=True)

class ProductOption(models.Model):
    """ 
    An option for a product.
    """
    product_type = models.ForeignKey(ProductType,related_name='options')
    name = models.CharField(max_length=100)
    
    def __unicode__(self):
        return self.name
    
    class Meta:
        unique_together = (('product_type','name'),)

class ProductOptionValue(models.Model):
    """ 
    A value for the product option.
    """
    product_option = models.ForeignKey(ProductOption,related_name='values')
    value = models.CharField(max_length=100)
    
    def __unicode__(self):
        return self.value
    
    class Meta:
        unique_together = (('product_option','value'),)

class Product(models.Model):
    """ 
    A searchable product.  May contain multiple SKUs or be a single SKU.
    """
    product_type = models.ForeignKey(ProductType,related_name='products')
    name = models.CharField(blank=True, max_length=100)
    slug = models.SlugField()
    categories = models.ManyToManyField(Category,related_name='products')
    default_sku = models.ForeignKey('SKU',related_name='default_product',null=True) # non-configurable products will have a defualt SKU.
    helper_content_type = models.ForeignKey(ContentType,related_name='products')
    helper_id = models.IntegerField()
    
    @property
    def helper(self):
        """ 
        Gets the helper object for this product.
        """
        return self.helper_content_type.model_class().objects.get(pk=self.helper_id)

class SKU(models.Model):
    """ 
    A sepcific configuration of a product.
    """
    product = models.ForeignKey(Product,related_name='skus')
    availability = models.ForeignKey(Availability,unique=True)

class SKUConfiguration(models.Model):
    """ 
    A specific product option value selection.
    """
    sku = models.ForeignKey(SKU,related_name='configurations')
    option = models.ForeignKey(ProductOption,related_name='sku_configurations')
    value = models.ForeignKey(ProductOptionValue,related_name='sku_configurations')
    
    def __unicode__(self):
        return u'%s : %s' % (unicode(self.option),unicode(self.value))
    
    class Meta:
        unique_together = (('sku','option'),)

    