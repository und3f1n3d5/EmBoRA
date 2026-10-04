"""Structural schema checks supplement the stricter cross-field validators."""
import re
from .schema import *


def validate_structure(schema, data, error=TraceError):
    if 'anyOf' in schema:
        for option in schema['anyOf']:
            try: validate_structure(option,data,error);return
            except ContractError: pass
        raise error('No schema alternative matches')
    if 'const' in schema and (type(data) is not type(schema['const']) or data!=schema['const']):raise error('Schema constant mismatch')
    if 'enum' in schema and data not in schema['enum']:raise error('Schema enum mismatch')
    kind=schema.get('type')
    if kind=='object':
        if type(data) is not dict:raise error('Schema object required')
        props=schema.get('properties',{});required=schema.get('required',[])
        if not set(required)<=set(data):raise error('Schema required field missing')
        for key,value in data.items():
            if key in props:validate_structure(props[key],value,error)
            elif schema.get('additionalProperties') is False:raise error('Schema unknown field')
            elif type(schema.get('additionalProperties')) is dict:validate_structure(schema['additionalProperties'],value,error)
    elif kind=='array':
        if type(data) is not list:raise error('Schema array required')
        for item in data:validate_structure(schema.get('items',{}),item,error)
    elif kind in ('number','integer'):
        value=real(data,error=error)
        if kind=='integer' and type(data) is not int:raise error('Schema integer required')
        if value<schema.get('minimum',-math.inf) or value>schema.get('maximum',math.inf):raise error('Schema number outside bounds')
    elif kind=='string':
        if type(data) is not str:raise error('Schema string required')
        if 'pattern' in schema and not re.fullmatch(schema['pattern'],data):raise error('Schema pattern mismatch')
    elif kind=='boolean' and type(data) is not bool:raise error('Schema Boolean required')
    elif kind=='null' and data is not None:raise error('Schema null required')


def validate_inventory(name,data,error=TraceError):
    schema=parse_json((Path(__file__).parent/'schemas'/name).read_text())
    validate_structure(schema,data,error)
