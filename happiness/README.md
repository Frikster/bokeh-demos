Happiness
=========

Happiness is a small web application that lets users in a company log in and record
their happiness.

Users are part of teams.  On their dashboard they can see a plot of their happiness over time
and their team's average happiness. If users are in more than one team they will see average
happiness for all their teams.

Managers can manage one or more teams. Their dashboard shows the average happiness for all the teams
they manage as well as individual lines for all the team members.

Django & Bokeh Server
=====================

Happiness is designed to demonstrate a simple setup of a django (or any other web framework - flask,
pyramid, etc) with the bokeh server.

The django webapp is used to authenticate users and store their data. The bokeh server is used
to serve up the plots to users and to keep that data uptodate by pushing down new data if its 
found in the database. 

This setup ensures that users only see the data they're allowed to. 

  $ conda create -n happiness --file conda-requirements.txt
  $ source activate happiness

Then in one terminal, start bokeh server

  $ ./bokeh.sh

And in a second terminal, start django
  
  $ ./manage.py runserver
