import numpy as np

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db import models
from django.db.models import Avg


class Team(models.Model):
    name = models.CharField(max_length=20, unique=True)
    manager = models.OneToOneField(User)

    def __str__(self):
        return '%s (%s)' % (self.name, self.manager.first_name)

    def get_team_dates_happiness(self, start_date=None, end_date=None):
        employees = self.employee_set.all()
        h_set = Happiness.objects.filter(employee__in=employees).order_by('date')
        average_happinesses = h_set.values('date').annotate(average_happiness=Avg('happiness'))
        dates = average_happinesses.values_list('date', flat=True)
        happinesses = average_happinesses.values_list('average_happiness', flat=True)
        return (np.array(dates), np.array(happinesses))


class Employee(models.Model):
    user = models.OneToOneField(User)
    teams = models.ManyToManyField('happiness.Team')

    def __str__(self):
        return '%s (%s)' % (self.user.first_name, self.teams_list)

    @property
    def teams_list(self):
        return ', '.join([team.name for team in self.teams.all()])

    def get_dates_happiness(self):
        h_set = self.happiness_set.order_by('date')
        dates = h_set.values_list('date', flat=True)
        happinesses = h_set.values_list('happiness', flat=True)
        return (np.array(dates), np.array(happinesses))


class Happiness(models.Model):
    employee = models.ForeignKey(Employee)
    date = models.DateField()
    happiness = models.DecimalField(decimal_places=0, max_digits=1)

    unique_together = (('employee', 'date'),)

    def get_absolute_url(self):
        return reverse('individual', kwargs={'pk': self.employee.user.pk})

    def __str__(self):
        return '%s %s %s' % (self.employee.user.first_name, self.happiness, self.date)
