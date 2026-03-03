from django.contrib import admin

from .models import LoanTag, Tag, TransactionTag

admin.site.register(Tag)
admin.site.register(TransactionTag)
admin.site.register(LoanTag)
