#!/usr/bin/python
import sys
import os
import optparse
#import bzrlib.builtins
from bzrlib.branch import Branch
from bzrlib.plugin import load_plugins
load_plugins()
import subprocess
import psycopg2
import ConfigParser
import socket
from mako.template import Template
from mako.runtime import Context
from StringIO import StringIO
import base64
import json
import requests
import getpass
import xmlrpclib
hostname=socket.gethostname()
DOMAIN=[('name','ilike',"%s%%"%hostname)]
def render_mako(template, context, fn=None):
    t=Template(template)
    if fn:
        buf=open(fn,'wb')
    else:
        buf=StringIO()
    ctx=Context(buf, **context)
    t.render_context(ctx)
    if fn:
        buf.close()
    else:
        return buf.getvalue()
sock=None
opt=None
uid=None
DEBUG=True
import getpass
import grp,pwd
import subprocess
from simplecrypt import encrypt, decrypt
import base64

def sudo_chown(fn,user,group,options=''): #-R

    if options:
        o=options.split()
    else:
        o=[]
    arg=["sudo","chown","%s:%s"%(user,group),fn]+o 
    ret=subprocess.call(arg)
    return ret
def sudo_mv(src, dst):
    arg=["sudo","mv",src,dst]
    ret=subprocess.call(arg)
    return ret

def run_chmod(fn, chmod):
    arg=["sudo","chmod",chmod,fn]
    if DEBUG:
        print arg
    subprocess.call(arg)

#import tempfile
#import shutil
def write_file(fn,c,user,group,chmod):
    current_login=getpass.getuser()
    USER=current_login
    GROUP=pwd.getpwnam(current_login).pw_name
    #temp_fp = tempfile.TemporaryFile(mode='wb')
    #temp_fp.write(c)
    #temp_fp.close(

    tmp='tmp_buff'
    #if DEBUG:
    #    print "Writing to tmpfile: ", tmp
    fp=open(tmp,'wb')
    fp.write(c)
    fp.close()
    sudo_chown(tmp, user, group)
    if DEBUG:
        print "Moving to destination : ", fn
    sudo_mv(tmp, fn)
    sudo_chown(fn, user, group)

    if chmod:
        run_chmod(fn,chmod)


def read(model,ids,fnames):
#    return sock.execute(dbname, uid, 'g77', 'deploy.repository', 'read',  clone_ids,['git_clone','mkdir'])
    #print opt.dbname, uid, opt.passwd, model, 'read',  ids,fnames
    ret =  sock.execute(opt.dbname, uid, opt.passwd, model, 'read',  ids,fnames)
    #print ret
    return ret
def write(model,ids,value):
    ret =  sock.execute(opt.dbname, uid, opt.passwd, model, 'write',  ids,value)
    return ret
def create(model,value):
    ret =  sock.execute(opt.dbname, uid, opt.passwd, model, 'create',  value)
    return ret

def search(model, domain):
    return sock.execute(opt.dbname, uid, opt.passwd, model, 'search', domain)

def update_one(model, arg, value):
    #print [model, arg, value]
    ret_ids = search(model, arg)
    if len(ret_ids)==1:
        ret = write(model, ret_ids, value)
        return ret_ids[0]
    elif len(ret_ids)==0:
        ret= create(model, value)
        return ret
    else:
        raise ValueError

import socket
import pprint
import resource
import os

def update_shmem(mem_total):
    pass

def run_bash(f_id,name,content,subprocess_arg):
    script_name=os.path.join(os.getcwd(), "script_%d.sh"%(f_id) )
    file(script_name,'wb').write(content)
    subprocess.call(["chmod","+x",script_name])

    arg = eval(subprocess_arg)
    print 44*'_'
    print 'Executing bash script name %s with args: %s'%( name, arg)
    ret=subprocess.call(arg )
    subprocess.call(["rm",script_name])
    return ret

def render_pass(content, pass_map,key):        
    for r in pass_map:
        tag=r['pass_tag']
        if tag in content:
            #print r
            p64=base64.decodestring( r['password'] )
            p=decrypt(key,p64)
            content=content.replace(tag,p)
    return content

def render(key):
    host_ids=search('deploy.host',DOMAIN)
    #print 'host ids', host_ids
    #host_explore(host_ids)

    ret=sock.execute(opt.dbname, uid, opt.passwd, 'deploy.host','render',host_ids, {'hostname':hostname})
    pass_ids=search('deploy.password',[] )
    pass_map=read('deploy.password', pass_ids,['pass_tag','password'] )
    #print len(ret[0])
    #h,model,t_id,r_id,out_file,content,user,group,_type,name,python_function,subprocess_arg,chmod,sequence
    for h,model,t_id,r_id,out_file,content,user,group,_type,name,python_function,subprocess_arg,chmod,sequence in ret:
        content=render_pass(content, pass_map,key)
        if _type=='template':
            write_file(out_file,content,user,group,chmod)
        elif _type=='python' and model=='deploy.host':
            my_code=compile(content, 'mypy', "exec")
            #print 'executing python code', [t_id,r_id,python_function]            
            exec my_code
            ret=eval(python_function)
        elif _type=='bash' and model=='deploy.host':            
            run_bash(t_id,r_id,name,content,subprocess_arg)

def password(cmd2,key):
    field_ids = search('ir.model.fields', [('relation','=','deploy.password')])
    fields = read('ir.model.fields', field_ids, ['name','model_id'] )
    for f in fields:
        print 44*'_'
        model_id,model = f['model_id']
        #print model_id, model
        res_ids = search(model, [])
        field_name = f['name']
        #print f,model, res_ids, field_name
        #print field_name
        records = read(model, res_ids, [field_name])
        for r in records:
            if field_name not in r:
                continue
            pname="PASS_%s_%s_%s"%(model.replace('.','_'),r['id'],field_name)
            if cmd2=='show':
                pr=r[field_name]
                print 'Model: %s, field: %s, res_id: %s' % (model, field_name, r['id'] )
                if pr:
                    p=read('deploy.password', r[field_name][0], ['name','password'])
                    print '   Passord [id] name: [%s] %s'% (p['id'], p['name'] )
                    password=p['password']
                    ps2=base64.b64decode(password)
                    print '   Encrypted password b64: [%s]'% password
                    x=decrypt(key,ps2)
                    print '   Decrypted password: [%s]'% x
                else:
                    print '   No password stored.'
            elif cmd2=='update':
                if not r[field_name]:
                    passwd=generate_password()
                    x=encrypt(key,passwd)
                    passwd2=base64.b64encode(x)
                    pass_id=create('deploy.password',{'name':pname,
                                                      'password':passwd2})
                    update_one(model,[('id','=',r['id'])],{field_name:pass_id})
            elif cmd2=='force_update' and False: #dangerous
                if 1:#not r[field_name]:
                    passwd=generate_password()
                    x=encrypt(key,passwd)
                    passwd2=base64.b64encode(x)

                    pass_id=create('deploy.password',{'name':pname,
                                                      'password':passwd2})
                    update_one(model,[('id','=',r['id'])],{field_name:pass_id})

def run(arg, user_id, host_id, key):
    #('template_id.type','in',['bash','python']),
    file_ids = search('deploy.file', arg)
    pass_ids=search('deploy.password',[] )
    pass_map=read('deploy.password', pass_ids,['pass_tag','password'] )

    files = read('deploy.file', file_ids, ['template_id',
                                           'command',
                                           'res_id',
                                           'encrypted',
                                           'sequence',
                                           'user',
                                           'group',
                                           'file_written',
                                           'content_written',
                                           'file_generated',
                                           'content_generated'])

    for f in files:
        t_id=f['template_id'][0]
        f_id=f['id']
        content_generated=f['content_generated']
        content=render_pass(content_generated, pass_map,key)
        t=read('deploy.mako.template', t_id, ['python_function',
                                              'subprocess_arg',
                                              'type',
                                              'name',
                                              'chmod'])
        _type=t['type']
        if _type=='template':
            file_generated=f['file_generated']

            chmod=t['chmod']
            user=f['user']
            group=f['group']
            write_file(file_generated, content,user,group,chmod)
            val={'file_written':file_generated,
                 'command':'run',
                 'content_written':content_generated}
            #print val
            write('deploy.file',f['id'], val)
        elif _type=='python':
            #content=f['content_generated']
            python_function=t['python_function']
            my_code=compile(content, 'mypy', "exec")
            #print 'executing python code', [t_id,r_id,python_function]            
            exec my_code
            ret=eval(python_function)
            val={'command':'run',
                 'content_written':''}
            #print val
            write('deploy.file',f['id'], val)

        elif _type=='bash':
            #content=f['content_generated']
            subprocess_arg=t['subprocess_arg']
            name=t['name']
            ret=run_bash(f_id,name,content,subprocess_arg)
            val={'command':'run',
                 'content_written':''}
            #print val
            write('deploy.file',f['id'], val)

    return

def init(cmd2, user_id, host_id):
    t_ids = search('deploy.mako.template', [('model','=',cmd2)] )
    templates = read('deploy.mako.template', t_ids,['name','domain'])
    i=0
    for t in templates:
        t_id=t['id']
        domain=t['domain']
        if domain:
            domain=domain.replace('active_user_id',str(user_id) )
            domain=domain.replace('active_host_id',str(host_id) )
            arg=eval(domain)
        else:
            arg=[]
        #print arg
        res_ids=search(cmd2, arg )

        for res_id in res_ids:
            arg=[('template_id','=',t_id),
                 ('user_id','=',user_id),
                 ('res_id','=',res_id)]

            val={'command':'init',
                 
                 'user_id':user_id,
                 'template_id':t_id,
                 'res_id':res_id,
                 'sequence':i}
            #print arg, val
            update_one('deploy.file',arg,val)
            i+=10

def data_export(master_data_module):
    m_id=search('ir.module.module', [('name','=',master_data_module)] )
    #print m_id,master_data_module
    if m_id:
        ret=sock.execute(opt.dbname,uid,opt.passwd, 'ir.module.module','master_data_export',m_id)
        print ret
def is_module(p):
    ret=False
    if os.path.isdir(p):
        init=os.path.join(p,'__init__.py')
        if os.path.isfile(init):
            terp=[os.path.join(p,'__openerp__.py'),
                  os.path.join(p,'__terp__.py'),
                  os.path.join(p,'__odoo__.py')]
            for t in terp:
                if os.path.isfile(t):
                    ret=True
    return ret
def get_local_dir(item):
    l=item['local_location_fnc']
    return l

def get_server(clone_ids):
    items = read('deploy.repository',clone_ids,['url','local_location_fnc'] )
    server_path=None
    spcnt=0 #allow only one server path
    c_id=False
    for c in items:
        a=get_local_dir(c) 
        if os.path.isdir(a):
            server=os.path.join(a,'openerp/addons/base')
            if os.path.isdir(server):
                server_path=a
                c_id=c['id']
                spcnt+=1
                if spcnt>1:
                    raise ValueError("only one server path allowed")
    return c_id,server_path

def get_parent_dir(path):
    arg=path.split('/')[-2:-1]
    arg=['/']+path.split('/')[:-1]
    p=os.path.join(*arg )
    return p
    
def get_addons(clone_ids):
    items = read('deploy.repository',clone_ids,['url','local_location_fnc','addon_subdir','is_module_path'] )
    addons_path=[]
    for c in items:
        a=get_local_dir(c) 
        to_append=False
        if c['is_module_path']:
            to_append=get_parent_dir(a)
        elif os.path.isdir(a):
            web=os.path.join(a, 'addons/web')
            add=os.path.join(a, 'addons')
            if c['addon_subdir']:
                add2=os.path.join(a, c['addon_subdir'] )
            else:
                add2=''
                
            if os.path.isdir(web) or os.path.isdir(add):
                to_append=os.path.join(a,'addons')

            elif os.path.isdir(add2):
                to_append=add2

            else:
                to_append=a
        addons_path.append( (c['id'],to_append) )
    return addons_path
def create_odoo_config(options, addons, fn='server7devel.conf', logfile=None):
    c=ConfigParser.RawConfigParser()
    cfn=os.path.join(fn)
    if 1:
        c.add_section('options')
        for o,v in options:
            c.set('options', o,v)
    c.set('options', 'addons_path', ','.join(list(set(addons))) )
    if logfile is not None:
        c.set('options', 'logfile', logfile)
    return c
def generate_config(clone_ids,options, fn=None, logfile=None):
    ret=get_addons(clone_ids)
    addons=[x[1] for x in ret if x[1]]
    c=create_odoo_config(options,addons,fn=fn,logfile=logfile)
    return c,ret

def bzr_pull(clone_ids):
    items = read('deploy.repository',clone_ids,['url','local_location_fnc'] )
    for c in items:
        
        #print c['mkdir']
        local_dir=get_local_dir(c)                
        cwd=os.getcwd()
        rb=c['url']
        if os.path.isdir(local_dir):
            os.chdir(local_dir)
            print 44*'_', 'bzr pull', local_dir
            args = ["bzr","pull", "--remember", rb]
            subprocess.call(args)
            os.chdir(cwd)

def git_clone(clone_ids):
    items = read('deploy.repository',clone_ids,['url','local_location_fnc','branch'] )
    for c in items:
        #print c['mkdir']
        local_dir=get_local_dir(c)      
        url=c['url']
        branch=c['branch']
        p=get_parent_dir(local_dir)
        if os.path.isdir(local_dir):
            pass       
        else:
            if not os.path.isdir(p):
                #if create_branch:
                os.makedirs(p) #create if it does not exist
            args = ["git","clone","--branch",branch, url,local_dir]
            print args
            ret=subprocess.call(args)
                #return out

def bzr_branch(clone_ids): #for existing branches, cmd can be push or pull
    items = read('deploy.repository',clone_ids,['url','local_location_fnc'] )
    for c in items:
        #print c['mkdir']
        local_dir=get_local_dir(c)                
        url=c['url']
        p=get_parent_dir(local_dir)
        if not os.path.isdir(p):
            os.makedirs(p) #create if it does not exist
            #    #print 'does not exist',  [rb, p, l]
        if not os.path.isdir(local_dir):
            r=Branch.open(url) #remote branch            
            new=r.bzrdir.sprout(local_dir) #new loca branch
#    return out

#def bzr_branch():
#    items = read('deploy.repositorye',clone_ids,['url','local_location_fnc'] )
#    for c in items:
#        print "#bzr url,local: %s,%s"%(c['url'], c['local_location_fnc'])
#        local=get_local_dir(c)       

def git_status(clone_ids):
    items = read('deploy.repository',clone_ids,['local_location_fnc'] )
    for c in items:
        #print c['mkdir']
        local_dir=get_local_dir(c)      
        #rb, branch,addon_subdir,is_module_path = xxx
        #local_dir, p, addon_path = git_remote2local(ROOT,xxx,subdir=subdir)
        cwd=os.getcwd()
        if os.path.isdir(local_dir):
            os.chdir(local_dir)
            print 44*'_', 'git', local_dir
            args = ["git","status","--branch"]
            subprocess.call(args)
            os.chdir(cwd)
def bzr_status(clone_ids):
    items = read('deploy.repository',clone_ids,['url','local_location_fnc'] )
    for c in items:
        #print c['mkdir']
        local_dir=get_local_dir(c)        
#
#    for rb,local in remote_branches:
        #rb, branch,addon_subdir,is_module_path = xxx
        #local_dir,p  = bzr_remote2local(ROOT,local)
        cwd=os.getcwd()
        if os.path.isdir(local_dir):
            os.chdir(local_dir)
            print 44*'_', 'bzr', local_dir
            args = ["bzr","status"]
            subprocess.call(args)
            os.chdir(cwd)

def git_push(clone_ids):
    items = read('deploy.repository',clone_ids,['url','local_location_fnc','branch'] )
    for c in items:
        #print c['mkdir']
        local_dir=get_local_dir(c)        
        #rb, branch,addon_subdir,is_module_path = xxx
        #local_dir, p, addon_path = git_remote2local(ROOT,xxx,subdir=subdir)
        cwd=os.getcwd()
        branch=c['branch']
        if os.path.isdir(local_dir):
            os.chdir(local_dir)
            print 44*'_', 'git push', local_dir
            args = ["git","push","origin", branch]
            subprocess.call(args)
            os.chdir(cwd)
def bzr_push(clone_ids):
    items = read('deploy.repository',clone_ids,['url','local_location_fnc'] )
    for c in items:
        #print c['mkdir']
        local_dir=get_local_dir(c)        
        cwd=os.getcwd()
        rb=c['url']
        if os.path.isdir(local_dir):
            os.chdir(local_dir)
            print 44*'_', 'bzr push', local_dir
            args = ["bzr","push", "--remember", rb]
            subprocess.call(args)
            os.chdir(cwd)

def git_pull(clone_ids):
    items = read('deploy.repository',clone_ids,['url','local_location_fnc','branch'] )
    for c in items:
        local_dir=get_local_dir(c)
        cwd=os.getcwd()
        branch=c['branch']
        if os.path.isdir(local_dir):
            os.chdir(local_dir)
            print 44*'_', 'git pull', local_dir
            args = ["git","pull","origin", branch]
            print args
            subprocess.call(args)
            os.chdir(cwd)


def get_wsgi(prod_config):
    return WSGI_SCRIPT % (prod_config)


def get_vhost(name, python_path, ServerName, WSGIScriptAlias, IP=None, PORT=None, processes=2, SSLCertificateFile=None, 
              SSLCertificateKeyFile=None, 
              SSLCACertificateFile=None,
              ProxyPass=None,
              Redirect=None,
              ssl=False, USER=None, GROUP=None, ROOT=None):
    if ssl and ( not SSLCertificateFile ) and (not SSLCertificateKeyFile ):
        SSLCertificateFile='/etc/apache2/ssl/apache.crt'
        SSLCertificateKeyFile='/etc/apache2/ssl/apache.key'
        if (not os.path.isfile(SSLCertificateFile) and not os.path.isfile(SSLCertificateKeyFile) ):
            if not os.path.isdir('/etc/apache2/ssl'):
                os.makedirs('/etc/apache2/ssl')
            subprocess.call( SELFSSL.split() )        
        if not PORT:
            PORT='443'
    else:
        if not PORT:
            PORT='80'
    if not IP:
        IP='127.0.0.1'
    if SSLCACertificateFile:
        intermediate=True
    else:
        intermediate=False

    arg = dict(name=name,
               python_path=python_path, 
               ServerName=ServerName, 
               ssl=ssl,
               user=USER,
               group=GROUP,
               ROOT=ROOT,
               WSGIScriptAlias=WSGIScriptAlias, 
               IP=IP, PORT=PORT, 
               processes=processes,
               SSLCertificateFile=SSLCertificateFile,
               ProxyPass=ProxyPass,
               Redirect=Redirect,
               SSLCertificateKeyFile=SSLCertificateKeyFile,
               #intermediate=intermediate,
               SSLCACertificateFile=SSLCACertificateFile)
    return render_mako(VHOST, arg)

user_list_sql="""SELECT u.usename AS "User name",
  u.usesysid AS "User ID",
  CASE WHEN u.usesuper AND u.usecreatedb THEN CAST('superuser, create
database' AS pg_catalog.text)
       WHEN u.usesuper THEN CAST('superuser' AS pg_catalog.text)
       WHEN u.usecreatedb THEN CAST('create database' AS
pg_catalog.text)
       ELSE CAST('' AS pg_catalog.text)
  END AS "Attributes"
FROM pg_catalog.pg_user u
ORDER BY 1"""

def create_or_update_db_user(options):
    o=dict(options)
    #if o['db_password']:
    #    
    #else:
    conn_string = "host='%s' dbname='postgres' user='%s' password='%s'" % (o['db_host'], o['db_user'],o['db_password'] )
    if 1:
        #print 'TRY: ', [conn_string]
        conn = psycopg2.connect(conn_string)
        cr = conn.cursor()
        print "user can connect"
        cr.close()
        conn.commit()
        
    conn_string = "host='%s' dbname='postgres' user='postgres' password='postgres'" % o['db_host']
    conn = psycopg2.connect(conn_string)
    cr = conn.cursor()
    cr.execute(user_list_sql)
    if o['db_user'] in [x[0] for x in cr.fetchall()]: #user exist?
        cr.execute("alter user %s with password '%s' " %( o['db_user'], o['db_password'] ) )
        cr.execute("alter user %s with superuser" %( o['db_user'], ) )
    else:
        cr.execute("create user %s with password '%s'"  %( o['db_user'], o['db_password'] ) )
    cr.close()
    conn.commit()
def run_sql(cs, sql):
    conn = psycopg2.connect(cs)
    cr = conn.cursor()
    ret=cr.execute(sql)
    d=cr.fetchall()
    #print "user can connect", cr, ret
    cr.close()
    conn.commit()
    return d

def sql_as_superuser(sql,port='5432'):
    conn_string1 = "host='%s' dbname='postgres' user='%s' port='%s'" % ('127.0.0.1', 'postgres',port)
    ret=run_sql(conn_string1, sql)
    if ret is None:        
        passwd=os.environ.get('PG_PASSWD')
        if passwd is None:
            passwd = getpass.getpass()
        conn_string = "host='%s' dbname='postgres' user='%s' port='%s' password='%s'" % ('127.0.0.1', 'postgres',passwd)
        ret=run_sql(conn_string, sql)
    return ret
    
exit_commands=['db','branch','write','status','unlink','push','pull', 'show']
def split_args(args):
    cmds=set(args).intersection(set(exit_commands))
    dbs=set(args)-cmds
    return list(cmds), list(dbs)

#def host_filter(ids, model='deploy.repository',field='local_host_id'):
def host_filter(ids, model=None,field=None):
    out=[]
    for h in read(model,ids,[field]):
        h_id,h_name=h[field]
        if hostname.startswith(h_name):
            out.append(h['id'])
    return out
def git_search(app_repository_ids):   
    ret = search('deploy.repository',[('type','=','git'),('id','in',app_repository_ids)] )
    return ret #host_filter(ret)
 
def bzr_search(app_repository_ids):
    ret = search('deploy.repository',[('type','=','bzr'),('id','in',app_repository_ids)] )
    return ret #host_filter(ret)
def deploy_search():
    return 
def get_user_id(user, hostname):
    host_id=update_one('deploy.host', [('name','=',hostname)], {'name':hostname} )
    user_id=update_one('deploy.host.user', [('login','=',user),('host_id.name','=',hostname)],
                       {'name':user,
                        'host_id':host_id,
                        'login':user,} )
    return user_id,host_id            

def generate_password():
    import string
    from random import sample, choice
    chars = string.letters + string.digits
    length = 8
    ret=''.join(choice(chars) for _ in range(length))
    return ret
def update_pg_user_passwd(user,passwd,port='5432'):
    sql="alter user %s with password '%s'"%(user,passwd)
    return sql_as_superuser(sql, port=port)

def update_clusters(host_id,key):
    #subprocess.call(["chmod","+x",script])
    s=subprocess.Popen(["pg_lsclusters","-h"], stdout=subprocess.PIPE)
    stdoutdata, stderrdata=s.communicate()
    #['9.3', 'main', '5432', 'online', 'postgres', '/var/lib/postgresql/9.3/main', '/var/log/postgresql/postgresql-9.3-main.log']
    #host_id=search('deploy.host'
    for c in stdoutdata.split('\n'):
        if c:
            print 'UPDATING', c
            version,name,port,status,user,data,log= c.split()
            arg=[('host_id','=',host_id),('version','=',version),
                 ('name','=',name),
             ]
            val=dict( [(x[0],x[2]) for x in arg] )
            val['port'] = int(port)
            pg_id=update_one('deploy.pg.cluster',arg,val)
            for pgu in sql_as_superuser(user_list_sql,port=port):
                print pgu
                name,pguid,perm=pgu
                #superuser=su=='superuser'
                arg=[('login','=',name),
                     ('cluster_id','=',pg_id) ]
                val=dict( [(x[0],x[2]) for x in arg] )
                val['superuser']=True#superuser                
                pg_user_id=update_one('deploy.pg.user',arg,val)
            pg_user_ids = search('deploy.pg.user',[('cluster_id','=',pg_id)])
            pg_users = read('deploy.pg.user',pg_user_ids,['login','password_id'])

def update_repository(repository_ids, user_id, host_id):
    out_ids=[]
    for c_id in repository_ids:
        c=read('deploy.repository',c_id,['use','type','name','branch',
                                         'addon_subdir',
                                         'is_module_path',
                                         'remote_name'])
        arg=[('remote_id','=',c_id),('local_user_id','=',user_id)]
        val={'remote_id':c_id,
             'local_user_id':user_id, 
             'addon_subdir': c['addon_subdir'],
             'is_module_path':c['is_module_path'],
             'remote_name':c['remote_name'],
             'use':c['use'],
             'branch':c['branch'],
             'type':c['type'],
             'host_id':host_id}
        r_id=update_one('deploy.repository',arg, val )
        out_ids.append(r_id)
    return out_ids
def validate_addon_path(repository_ids):
    ret=get_addons(repository_ids)
    for c_id, addon_path in ret:
        arg=[('id','=',c_id)]
        val={'validated_addon_path':addon_path}
        #print val
        r_id=update_one('deploy.repository',arg, val )

def apps2repository(application_ids):
    apps = read('deploy.application', application_ids, ['name','repository_ids'] )
    app_repository_ids=[]
    for a in apps:
        for ar_id in a['repository_ids']:
            if ar_id not in app_repository_ids:
                app_repository_ids.append(ar_id)
    return app_repository_ids
    
def update_deployments(opt,app_ids, user_id, pg_user_id, name='%'):
    #r_ids = apps2repository(app_ids)
    user = read('deploy.host.user', user_id, ['name','login','home'])
    ROOT=user['home']

    ROOT=os.path.join(ROOT, opt.subdir)
    if not os.path.isdir(ROOT):
        os.makedirs(ROOT) #create if it does not exist

    for app_id in app_ids:
        arg=[('application_id','in',[app_id]),('user_id','=',user_id),('pg_user_id','=',pg_user_id),
             ('name','ilike',name)]
        val={'application_id':app_id,
             'pg_user_id':pg_user_id,
             'user_id':user_id,
        }
        update_one('deploy.deploy',arg, val)

        deploy_ids = search('deploy.deploy',arg)
        for d_id in deploy_ids:
            d=read('deploy.deploy', d_id, ['odoo_config','clone_ids'])
            clone_ids = d['clone_ids']
        
            c_id,server_path=get_server(clone_ids)
            print server_path
            c=d['odoo_config']
            if os.path.isfile(c):
                validated_config_file = c
            else:
                validated_config_file = ''
            if server_path and os.path.isdir(server_path):
                validated_server_path = server_path
            else:
                validated_server_path = ''
            val={'application_id':app_id,
                 'pg_user_id':pg_user_id,
                 'user_id':user_id,
                 'validated_config_file': validated_config_file,
                 'validated_server_path': validated_server_path,
                 'validated_root':ROOT,
             }
            update_one('deploy.deploy',arg, val)

def parse(sys_args):
    
    import getpass
    current_login=getpass.getuser()
    #if ROOT is None:
    #    ROOT=os.environ['HOME']
    if 'PASS' in os.environ:
        PASS=os.environ['PASS']
    else:
        PASS=None
    #if USER is None:
    USER=current_login
    #if GROUP is None:
    #    import grp,pwd
    GROUP=pwd.getpwnam(current_login).pw_name
    if PASS:
        key=PASS
    else:
        key=getpass.getpass()

    hostname=socket.gethostname()
    usage = "usage: python %prog [options] cmd1, cmd2, .. [db1, db2, ...]\n"
    usage += "  Commands: %s \n" % (','.join(exit_commands) )
    parser = optparse.OptionParser(version='0.1', usage=usage)

    group = optparse.OptionGroup(parser, "Login")

    group.add_option("--api-url",
                     dest='apiurl',
                     help="Default: [%default]",
                     #default='http://golive-ontime.co.uk:8066/'
                     default='http://localhost:10069/'
                     )
    group.add_option("--login",
                     dest='login',
                     help="Default: [%default]",
                     default='admin'
                     )
    group.add_option("--pass",
                     dest='passwd',
                     help="Default: [%default]",
                     default='admin'
                     )
    group.add_option("--dbname",
                     dest='dbname',
                     help="Default: [%default]",
                     default='deploy'
                     )
    group.add_option("--subdir",
                     dest='subdir',
                     help="Default: [%default]",
                     default='projects'
                     )

    parser.add_option_group(group)
    global uid
    global sock
    global opt
    opt, args = parser.parse_args(sys_args)
    sock_common = xmlrpclib.ServerProxy (opt.apiurl+'xmlrpc/common')
    uid = sock_common.login(opt.dbname, opt.login,opt.passwd)
    sock = xmlrpclib.ServerProxy(opt.apiurl+'xmlrpc/object')
    user_id,host_id=get_user_id(USER, hostname)

    user_apps=read('deploy.host.user',user_id, ['app_ids'])

    application_ids=user_apps['app_ids']#search('deploy.application',[])

    app_repository_ids = apps2repository(application_ids)
    update_repository(app_repository_ids, user_id, host_id)
    arg=[('local_user_id','=',user_id),
         ('use','in',['server','addon']),
         ('remote_id','in',app_repository_ids)]
    local_r_ids = search('deploy.repository',arg)
    validate_addon_path(local_r_ids)


    arg=[('local_user_id','=',user_id),
         ('remote_id','in',app_repository_ids)]
    local_r_ids = search('deploy.repository',arg)
    #validate_addon_path(local_r_ids)
    git_ids=git_search(local_r_ids)
    bzr_ids=bzr_search(local_r_ids)


    if len(args)==1:
        cmd=args[0]
        if cmd=='clone':
            git_clone(git_ids)
            bzr_branch(bzr_ids)
        elif cmd=='status':
            git_status(git_ids)
            bzr_status(bzr_ids)
        elif cmd=='pull':
            git_pull(git_ids)
            bzr_pull(bzr_ids)
            update_repository(app_repository_ids,user_id, host_id)
        elif cmd=='push':
            git_push(git_ids)
            bzr_push(bzr_ids)
        elif cmd=='pg':
            cluster_ids = update_clusters(host_id,key)
        elif cmd=='run':
            arg=[('user_id','=',user_id)]
            run(arg, user_id, host_id,key)
            
    elif len(args) in [2]:
        cmd,cmd2=args
        if cmd=='init':
            init(cmd2, user_id, host_id)
        elif cmd=='run':
            arg=[('user_id','=',user_id), ('template_id.model','=',cmd2)]
            run(arg, user_id, host_id,key)
        elif cmd=='password':
            password(cmd2,key)
        elif cmd=='encrypt':
            x=encrypt(key,cmd2)
            t=base64.b64encode(x)
            print [t]
            d = base64.decodestring( t )
            print [decrypt(key,d)]
        elif cmd=='export':
            data_export(cmd2)
        elif cmd=='config' and cmd2=='show':
            deploy_ids=search('deploy.deploy',[('user_id','=',user_id)])
            #deploy_ids = host_filter(deploy_ids,model='deploy.deploy',field='host_id')
            dps=read('deploy.deploy',deploy_ids,['site_name',
                                                 'options',
                                                 'db_password',
                                                 'admin_password',
                                                 #'repository_ids',
                                                 'odoo_config',
                                                 'validated_config_file',
                                                 'validated_server_path',
                                                 ])
            for d in dps:
                print 44*'__'
                print "%s/openerp-server -c %s"%( d['validated_server_path'],d['odoo_config'] )
                #print 'Addon paths:'
                #repository_ids = d['repository_ids']
                #clones=read('deploy.repository',repository_ids,['validated_addon_path','name',
                #                                                      'local_location'])
                #for c in clones:
                #    print c['name'], c['validated_addon_path']
    elif len(args)==4:
        cmd,cmd2,dbuser,apps_str=args
        pg_user_ids=search('deploy.pg.user',[('login','=',dbuser),('cluster_id.host_id.name','=',hostname)] )
        assert len(pg_user_ids)==1
        pg_user_id=pg_user_ids[0]
        if apps_str=='all':
            app_arg=[('id','in',application_ids)]
        else:
            app_arg=[('name','in', app_str.split(',') ), ('id','in',application_ids) ]
        update_app_ids=search('deploy.application',app_arg)

        if cmd=='update' and cmd2=='deployments':
            for app_id in update_app_ids:
                a=read('deploy.application', app_id, ['name'])
                app_name = a['name']
                arg=[('application_id','=',app_id),('user_id','=',user_id),('pg_user_id','=',pg_user_id)]
                val={'application_id':app_id,
                     'user_id':user_id,
                     'pg_user_id':pg_user_id}
                d_id=update_one('deploy.deploy',arg, val)
                d=read('deploy.deploy', d_id, ['name','site_name','mode'])
                if not d['name']:
                    write('deploy.deploy',d_id,{'name':app_name})
                if not d['site_name']:
                    write('deploy.deploy',d_id,{'site_name':app_name})
                if not d['mode']:
                    write('deploy.deploy',d_id,{'mode':'dev'})
        

        #elif len(args)==3:
        #cmd,cmd2,dbuser=args
        #pg_user_ids=search('deploy.pg.user',[('login','=',dbuser),('cluster_id.host_id.name','=',hostname)] )
        #assert len(pg_user_ids)==1
        #pg_user_id=pg_user_ids[0]

        if cmd=='validate' and cmd2=='config':

            update_deployments(opt,update_app_ids, user_id, pg_user_id, name='%')

        elif cmd=='config' and cmd2=='write': #deprecated
            pg_user_ids=search('deploy.pg.user',[('login','=',dbuser),('cluster_id.host_id.name','=',hostname)] )
            assert len(pg_user_ids)==1
            pg_user_id=pg_user_ids[0]

            if PASS:
                key=PASS
            else:
                key=getpass.getpass()
            application_ids=search('deploy.application',[])
            apps = read('deploy.application', application_ids, ['name','repository_ids'] )
            for app in apps:

                app_name=app['name']
                app_id=app['id']
                repository_ids=app['repository_ids']

                #prod_config=os.path.join(ROOT, 'server7%s.conf'%app_name)               
                arg=[('application_id','=',app_id),('user_id','=',user_id),('pg_user_id','=',pg_user_id)]
                deploy_ids=search('deploy.deploy',arg)
                dps =read('deploy.deploy',[deploy_ids],['site_name',
                                                        'password_id',
                                                        'options_id',
                                                        'application_id'])
                for d in dps:
                    if d['options_id']:
                        pass
                    else:
                        options_ids=search('deploy.options',[('name','=','dev')])
                        update_one('deploy.deploy',[('id','=',d['id'])],
                                   {'options_id':options_ids[0] })
                        
                dps =read('deploy.deploy',[deploy_ids],['site_name',
                                                        'odoo_config',
                                                        'options',
                                                        'db_password',
                                                        'admin_password',
                                                        'application_id'])
                assert len(dps)==1
                d=dps[0]
                prod_config = d['odoo_config']
                with open(prod_config, 'wb') as cf:
                    print 'writing config: ', prod_config
                    options=eval(d['options'])
                    db_pass=d['db_password']
                    admin_pass=d['admin_password']                    
                    db_pass=base64.decodestring(db_pass)
                    admin_pass=base64.decodestring(admin_pass)
                    options.append( ('db_password', decrypt(key,db_pass)) )
                    options.append( ('admin_password', decrypt(key,admin_pass)) )
                    conf,ret=generate_config(repository_ids,options)
                    conf.write(cf)

                    for c_id,addon_path in ret:
                        arg=[('remote_id','=',c_id),('local_user_id','=',user_id)]
                        val={'remote_id':c_id,
                             'local_user_id':user_id, 
                             'validated_addon_path':addon_path}
                        update_one('deploy.repository',arg, val )

                    c_id,server_path=get_server(repository_ids)
                    arg=[('application_id','=',app_id),('user_id','=',user_id)]
                    val={'application_id':app_id,
                         'user_id':user_id,
                         'validated_config_file':prod_config,
                         'validated_server_path':server_path,
                         'validated_root':ROOT}
                    update_one('deploy.deploy',arg, val)

    return
if __name__ == '__main__':
    parse(sys.argv[1:])
