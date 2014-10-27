#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2014 uralbash <root@uralbash.ru>
#
# Distributed under terms of the MIT license.

"""
CREATE, READ, DELETE, UPDATE actions for SQLAlchemy models
"""
import transaction

from sacrud.common import (columns_by_group, get_empty_instance, get_obj,
                           get_pk, ObjPreprocessing, RequestPreprocessing)

prefix = 'crud'


def set_m2m_value(session, request, obj):
    """ Set m2m value for model obj from request params like "group[]"

        :Parameters:

            - `session`: SQLAlchemy DBSession
            - `request`: request as dict
            - `obj`: model instance
    """
    def get_m2m_objs(session, relation, ids):
        pk = relation.primary_key[0]
        return session.query(relation).filter(pk.in_(ids)).all()

    m2m_request = {k: v for k, v in list(request.items()) if k[-2:] == '[]'}
    for k, v in list(m2m_request.items()):
        key = k[:-2]
        relation = getattr(obj.__class__, key, False)
        if not relation:
            continue  # pragma: no cover
        value = get_m2m_objs(session, relation.mapper, v)
        setattr(obj, key, value)
    return obj


class CRUD(object):
    """ Main class for CRUD actions

        :Parameters:

            - `session`: SQLAlchemy DBSession
            - `table`: SQLAlchemy model
            - `pk`: obj primary keys
            - `request`: web request
    """
    def __init__(self, session, table, pk=None, request=None):
        self.pk = get_pk(table)
        self.table = table
        self.request = request
        self.session = session
        self.obj = get_obj(session, table, pk)

    def rows_list(self):
        """
        Return a list of table rows.

        :Parameters:

            - `order_by`: name ordered row.
            - `paginator`: see sacrud.common.paginator.get_paginator.
        """
        table = self.table
        session = self.session
        col = [c for c in getattr(table, 'sacrud_list_col',
                                  table.__table__.columns)]
        row = session.query(table)
        return {'row': row,
                'pk': self.pk,
                'col': col,
                'table': table,
                'prefix': prefix,
                }

    def add(self):
        """ Update row of table.

        :Example:

        .. code-block:: python

            resp = action.CRUD(dbsession, table, pk)
            resp.request = params
            resp.add()

        """

        if self.request:
            # Make empty obj for create action
            if not self.obj:
                self.obj = get_empty_instance(self.table)

            request_preprocessing = RequestPreprocessing(self.request)

            # filter request params for object
            for key in list(self.request.keys()):
                # chek if columns not exist
                if key not in self.table.__table__.columns and\
                        not hasattr(self.table, key):
                    if key[-2:] != '[]':
                        self.request.pop(key, None)
                    continue  # pragma: no cover
                self.request[key] = request_preprocessing.check_type(self.table, key)
                self.obj.__setattr__(key, self.request[key])

            # save m2m relationships
            self.obj = set_m2m_value(self.session, self.request, self.obj)
            self.session.add(self.obj)
            transaction.commit()
            return self.obj
        columns = columns_by_group(self.table)
        return {'obj': self.obj,
                'pk': self.pk,
                'col': columns,
                'table': self.table,
                'prefix': prefix}

    def delete(self, commit=True):
        """ Delete row by pk.

        :Example:

        .. code-block:: python

            action.CRUD(dbsession, table, pk=pk).delete()

        If you no needed commit session

        .. code-block:: python

            action.CRUD(dbsession, table, pk=pk).delete(commit=False)
        """
        obj = ObjPreprocessing(obj=self.obj).delete()
        self.session.delete(obj)
        if commit is True:
            transaction.commit()
        return self.pk
