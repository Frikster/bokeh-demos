from __future__ import print_function

import pandas as pd

from threading import Thread
import requests
from requests.exceptions import ConnectionError

import utils
import ui
from bokeh.plotting import figure, show
from bokeh.io import output_file
from bokeh.models.sources import ColumnDataSource, AjaxDataSource
from bokeh.models.widgets import (HBox, VBox, VBoxForm, PreText, CheckboxGroup,
                                  Select, AppHBox, AppVBox, AppVBoxForm,
                                    Paragraph, Dialog, Tabs, Panel,
                                  AutocompleteInput, Button, TextInput)


from bokeh.embed import components, autoload_server
from bokeh.resources import Resources
from bokeh.templates import RESOURCES

from flask import render_template, request

import utils
from utils import create_output


from bokeh.simpleapp import simpleapp
from bokeh.server.app import bokeh_app

from bokeh.plotting import curdoc, cursession
from bokeh.appmaker import bokeh_app, curdoc, SimpleApp
# TODO: WE CAN AVOID THISS!!!!
from flask import jsonify

from datasources import *

POLL_TIME = 1000
selected_airport_id = '3682'
# airport = utils.get_airport_data(selected_aiport_id, utils.airports)
# ap_routes = utils.get_routes(airport)
# ap_routes_source = ColumnDataSource(ap_routes, tags=['routes_source'])
# all_airports = ColumnDataSource(create_output(utils.airports), tags=['main_source'])
# airports_found_source = ColumnDataSource(tags=['airports_found_source'])

# Prepare data
airports = utils.airports = pd.read_csv(
    '../data/airports.dat',
    names=['id', 'name', 'city', 'country', 'iata', 'icao', 'lat', 'lng', 'alt', 'dst', 'tz', 'tz_db']
)

airports['lname'] = [x.lower() for x in airports.name]
airports['lcity'] = [x.lower() for x in airports.city]
airports['liata'] = [str(x).lower() for x in airports.iata]

routes = utils.routes = pd.read_csv(
    '../data/routes.dat',
    names=['airline', 'id', 'source_ap', 'source_ap_id', 'dest_ap', 'dest_ap_id', 'codeshare', 'stops', 'equip']
)

sources = set([int(sid)for sid in routes.source_ap_id if sid.isdigit()])
dests = set([int(sid)for sid in routes.dest_ap_id if sid.isdigit()])
active_ap_ids = sources.union(dests)

out_routes = routes.groupby('source_ap_id').count().sort('id', ascending=False)

airport = utils.get_airport_data(selected_airport_id, utils.airports,
                                 routes, out_routes, active_ap_ids)
ap_routes = utils.get_routes(airport)
ap_routes_source = ColumnDataSource(ap_routes, tags=['routes_source'])
_source_aps = create_output(airport['destinations'])
_all_aps = create_output(utils.airports)
all_airports = ColumnDataSource(_all_aps, tags=['main_source'])

airports_found_source = ColumnDataSource(tags=['airports_found_source'])

worldmap_source = ColumnDataSource(utils.get_worldmap(airports, routes))
worldmap_source.data['alpha'] = [1 for x in worldmap_source.data['alpha']]

population_source = ColumnDataSource(ColumnDataSource.from_df(population))

legend_source = ColumnDataSource(
    {'name': ['>300', '200-300', '100-200', '50-100', '10-50', '1-10', '>=1'],
            'x': [25] * 7,
            'y': [11, 27, 39, 50, 60, 70, 80],
            'radius': [8*x for x in [1.5, 1, 0.8, 0.5, 0.3, 0.2, 0.1]]
    },
    tags=['legend_source']
)
freq_legend_source = ColumnDataSource(
    {'name': ['>300', '200-300', '100-200', '50-100', '10-50', '1-10', '<=1'],
            'x': [35] * 7,
            'x_int': [55] * 7,
            'y': [10*x for x in range(1, 8)],
            'alpha': [0.1*x for x in range(1, 8)]
    },
    tags=['legend_source']
)


# Widgets
btn_search = Button(label='search', name='search_button', classes=['topbutton'])
btn_cancel_search = Button(label='cancel', name='cancel_search', classes=['topbutton'])

select_city_size = CheckboxGroup(
        labels=['1', '1-10', '10-50', '50-100', '100-200', '200-300', '>300'],
        name='select_city_size', inline=True,
    )

cumulate_paths = CheckboxGroup(labels=['cumulate paths'],
                               name='paths', inline=True,
                               )

label_city_filter = Paragraph(text='Filter city by number of routes:',
                              name='label_city_filter',
                              height=25)

btn_selected_airport = Button(label=airport['airport'].name.values[0],
                              name='btn_selected_airport', classes=['topbutton'])


def create_airport_map(theme):
    # create plot object and add all it's objects
    plot = figure(title="Flights", plot_width=900, plot_height=600, toolbar_location='right',
                  y_range=(-50, 90), x_range=(-160, 155),
                  tools="pan,box_zoom,tap,resize,reset")

    ui.create_airport_map(plot, ap_routes_source, all_airports,
                          worldmap_source, theme=theme)

    route_freq_legend = ui.create_route_freq_legend(freq_legend_source, theme)
    int_ext_route_legend = ui.create_int_ext_route_legend(theme)

    return {
        'main_map': plot,
        'route_freq_legend': route_freq_legend,
        'int_ext_route_legend': int_ext_route_legend,
    }

def create_frequency_map(theme):
    # create plot object and add all it's objects
    plot = figure(title="Flights", plot_width=900, plot_height=600,
                  toolbar_location='right', y_range=(-50, 90), x_range=(-150, 160),
                  tools="pan,box_zoom,hover,crosshair,resize,reset")

    ui.create_population_map(plot, population_source, worldmap_source, theme=theme)

    return {
        'frequency_map': plot,
        'pop_alpha_legend': ui.create_alpha_legend(freq_legend_source, theme),
        'city_population_legend': ui.create_size_legend(legend_source, theme),
    }


@simpleapp(btn_search, btn_cancel_search, select_city_size, label_city_filter, btn_selected_airport,
           cumulate_paths)
def app(search_button):
    # retrieve the theme to be used..
    theme = 'dark'
    searchbox = TextInput(classes=['appsearch'])

    # create plot object and add all it's objects

    info_txt = PreText(text=airport['summary'], width=200, height=250)

    dest_sources = ColumnDataSource(utils.create_dests_source(airport, utils.airports))
    starburst = ui.create_starburst(ap_routes_source, dest_sources, theme=theme)
    dlg_info = Dialog(title='Selected Airport Info',
                      content=VBox(info_txt, starburst),
                      visible=False
    )

    objects = {
        'info_txt': info_txt,
        'starburst': starburst,
        'searchbox': searchbox,
        'dlg_info': dlg_info,
    }

    objects.update(ui.create_dlg_airports_list(airports_found_source))
    objects.update(create_frequency_map(theme))
    objects.update(create_airport_map(theme))

    return objects

@app.layout
def stock2_layout(app):
    topbar = AppHBox(app=app, children=[
        Paragraph(text='Worldwide Flight Networks', width=400, height=10, classes=['apptitle']),
        'btn_selected_airport',
        Paragraph(width=200),
        'searchbox', 'search_button',
        ], classes=['topbar'])
    sidebar = AppVBox(app=app, children=[
        Paragraph(height=260),
        'int_ext_route_legend',
        Paragraph(height=10),
        'route_freq_legend',
         Paragraph(height=1),
         # 'legend',
    ])
    mainbox = AppHBox(app=app, children=[
        'dlg_airports_found', 'dlg_info',
        sidebar,
        'main_map']
    )
    popsidebar = AppVBox(app=app, children=[Paragraph(height=150), 'city_population_legend', 'pop_alpha_legend'])
    population_box = AppHBox(app=app, children=[popsidebar, 'frequency_map']
    )
    tabs = Tabs(tabs=[Panel(title='Flight Frequency', child=population_box),
                      Panel(title='Flight Networks', child=mainbox), ])
    app = AppVBox(app=app, children=[topbar, tabs])
    return app

@app.update([({'tags' : 'main_source'}, ['selected'])])
def update_selection(app):
    # select the sources we want to change uppon selection
    theme = 'creme'

    source = app.select_one({'tags' : 'main_source'})
    routes_source = app.select_one({'tags' : 'routes_source'})

    # get the selected airport ID and change the selected airport accordingly
    try:
        id_ = source.selected['1d']['indices'][0]
        airport_id = str(int(source.data['id'][id_]))
        # airport = utils.get_airport_data(airport_id, utils.airports)
        airport = utils.get_airport_data(airport_id, utils.airports,
                                        routes, out_routes,
                                        active_ap_ids)

        objs = update_current_airport(airport_id, source, routes_source, app, theme)

        return objs
    except IndexError:
        pass


@app.update([({'tags' : 'legend_source'}, ['selected'])])
def update_legend_selection(app):
    # select the sources we want to change uppon selection
    theme = 'creme'

    source = app.select_one({'tags' : 'legend_source'})
    main_source = app.select_one({'tags' : 'main_source'})
    ind = source.selected['1d']['indices'][0]

    data = source.data
    radius_to_check = float(source.data['radius'][ind]) / 8.

    for i, value in enumerate(main_source.data['radius']):
        if float(value) == radius_to_check:
            main_source.data['color'][i] = None

@app.update([({'name' : 'search_button'}, ['clicks'])])
def on_search(searchbox, app):
    txt = app.objects['searchbox'].value or ''

    aps_found = utils.search_airports(txt.lower(), utils.airports)


    source = app.select_one({'tags' : 'airports_found_source'})
    # source = app.objects['airports_found_source']
    source.data = create_output(aps_found, ['name', 'country', 'city', 'iata'])

    objects = ui.create_dlg_airports_list(source)

    objects['dlg_airports_found'].visible = True

    return objects



@app.update([({'name' : 'btn_selected_airport'}, ['clicks'])])
def on_selected_airport(searchbox, app):
    new_dlg = Dialog(title='Selected Airport Info', #buttons=[confirm_chart_button],
                        content=HBox(app.objects['info_txt'], app.objects['starburst']), visible=True)
    return {'dlg_info': new_dlg}


@app.update([({'name' : 'cancel_search'}, ['clicks'])])
def on_cancel(searchbox, app):
    app.objects['searchbox'].value = ''
    return {'searchbox': app.objects['searchbox']}


@app.update([({'tags' : 'airports_found_source'}, ['selected'])])
def airport_row_selected(searchbox, app):
    # TODO: WHY THIS DOESN'T WORK????????
    source = app.select_one({'tags' : 'airports_found_source'})
    print ("NOT WORKING!!!!")


@app.update([({'name' : 'btn_airport_selected'}, ['clicks'])])
def on_confirm_airport_selection(searchbox, app):
    theme = 'creme'
    app.objects['dlg_airports_found'].visible = False

    source = app.select_one({'tags' : 'main_source'})
    routes_source = app.select_one({'tags' : 'routes_source'})
    objects = update_current_airport(selected_aiport_id, source, routes_source, app, theme)
    app.objects['searchbox'].value = ''
    objects['searchbox'] = app.objects['searchbox']
    return objects


def update_current_airport(airport_id, source, routes_source, app, theme):
    # airport = utils.get_airport_data(aiport_id, utils.airports)
    airport = utils.get_airport_data(airport_id, utils.airports,
                                    routes, out_routes,
                                    active_ap_ids)

    # update the sources with the new data
    routes_source.data = utils.get_routes(airport)
    source.data = create_output(utils.airports)

    # update the summary text
    app.objects['info_txt'].text = airport['summary']
    curr_ap_btn = app.select_one({'name': 'btn_selected_airport'})
    curr_ap_btn.label = airport['airport'].name.values[0]

    dest_sources = ColumnDataSource(utils.create_dests_source(airport, utils.airports))
    starburst = ui.create_starburst(routes_source, dest_sources, theme=theme)

    return {
        'info_txt': app.objects['info_txt'],
        'starburst': starburst,
    }

napp = SimpleApp.create(app.name, app.widgets)

curdoc().clear()
curdoc().add(napp)