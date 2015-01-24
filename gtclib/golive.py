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

def chown(fn,user,group,options=''): #-R

    if options:
        o=options.split()
    else:
        o=[]
    
    ret=subprocess.call(["chown","%s:%s"%(user,group),fn]+o )
    #print [ret]
    return ret
def run_chmod(fn, chmod):
    arg=["chmod",chmod,fn]
    if DEBUG:
        print arg
    subprocess.call(arg)

def write_file(fn,c,user,group,chmod):
    current_login=getpass.getuser()
    USER=current_login
    GROUP=pwd.getpwnam(current_login).pw_name
    
    if DEBUG:
        print "Writing to: ", fn
    try:
        fp=open(fn,'wb')
        fp.write(c)
        fp.close()
    except IOError:
        if DEBUG:
            print "   Can not create/write to: ", fn
    if (user!=USER) or (group!=GROUP):
        if DEBUG:
            print "   Current user: %s"%USER
            print "   Current group: %s"%GROUP
            print "   Chmod to: %s:%s"%(user,group)
        chown(fn,user,group)
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

def run_bash(t_id,r_id,name,content,subprocess_arg):
    script=os.path.join(os.getcwd(), "script_%d_%d.sh"%(t_id,r_id) )
    file(script,'wb').write(content)
    subprocess.call(["chmod","+x",script])
    #print [name, subprocess_arg]
    arg=eval(subprocess_arg)
    print '   executing bash script', name,script,arg

    subprocess.call(arg )
    #print '   deleting bash script', script
    subprocess.call(["rm",script])


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

def get_server(clone_ids):
    items = read('deploy.repository',clone_ids,['url','local_location_fnc'] )
    server_path=None
    spcnt=0 #allow only one server path
    c_id=False
    #print 'GET SERVER'
    for c in items:
        a=get_local_dir(c) 
        #print c,a
        if os.path.isdir(a):
            server=os.path.join(a,'openerp/addons/base')
            #web=os.path.join(a, 'addons/web')
            #add=os.path.join(a, 'addons')
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
    #print 'Parent Dir for ', path, arg,p
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
def get_local_dir(item):
    #current_login=getpass.getuser()
    HOME=os.environ['HOME']
    l=item['local_location_fnc']
    if l.startswith('/'):
        return l
    else:
        return os.path.join(HOME,l)

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
        #print c['mkdir']
        local_dir=get_local_dir(c)
#    for xxx in remote_branches:
 #       rb, branch,addon_subdir,is_module_path = xxx
  #      local_dir, p, addon_path = git_remote2local(ROOT,xxx,subdir=subdir)
        cwd=os.getcwd()
        branch=c['branch']
        if os.path.isdir(local_dir):
            os.chdir(local_dir)
            print 44*'_', 'git pull', local_dir
            args = ["git","pull","origin", branch]
            print args
            subprocess.call(args)
            os.chdir(cwd)

WSGI_SCRIPT="""import sys
import openerp
openerp.tools.config.parse_config(['--config=%s'])
application = openerp.service.wsgi_server.application
""" 

def get_wsgi(prod_config):
    return WSGI_SCRIPT % (prod_config)

VHOST="""<VirtualHost ${IP}:${PORT}>
        ServerName ${ServerName}
        %if ServerAlias:
            ServerAlias ${ServerAlias}
        %endif
        %if ssl:
           SSLEngine on
           SSLCertificateFile ${SSLCertificateFile}
           SSLCertificateKeyFile ${SSLCertificateKeyFile}
        %endif
        %if SSLCACertificateFile:
           SSLCACertificateFile ${SSLCACertificateFile}
        %endif
        %if ProxPass:
            ProxyPass / ${ProxyPass}
            ProxyPassReverse / ${ProxyPass}
        %elif Redirect:
            #Redirect permanent / https://secure.example.com/
            Redirect / ${Redirect}
        %else:
        <%
          apache_log_dir="${APACHE_LOG_DIR}"
        %>
        WSGIScriptAlias / ${WSGIScriptAlias}
        WSGIDaemonProcess ${name} user=${user} group=${group} processes=${processes} python-path=${python_path} display-name=${name}
        WSGIProcessGroup ${name}
        <Directory ${python_path}>
            Order allow,deny
            Allow from all
        </Directory>
        ErrorLog ${apache_log_dir}/openerp-${name}-error.log
        # Possible values include: debug, info, notice, warn, error, crit,                                                                                                                                         
        # alert, emerg.                                                                                                                                                                                            
        LogLevel debug
        CustomLog ${apache_log_dir}/openerp-${name}.log combined

        %endif
</VirtualHost>
"""

SELFSSL="openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout /etc/apache2/ssl/apache.key -out /etc/apache2/ssl/apache.crt"

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

#def host_filter(ids, model='deploy.repository.clone',field='local_host_id'):
def host_filter(ids, model=None,field=None):
    out=[]
    for h in read(model,ids,[field]):
        h_id,h_name=h[field]
        if hostname.startswith(h_name):
            out.append(h['id'])
    return out
def git_search():   
    ret = search('deploy.repository',[('type','=','git')] )
    return ret #host_filter(ret)
 
def bzr_search():
    ret = search('deploy.repository',[('type','=','bzr')] )
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
            for pg in pg_users:
                if not pg['password_id']:
                    passwd=generate_password()
                    x=encrypt(key,passwd)
                    passwd2=base64.b64encode(x)
                    pass_id=create('deploy.password',{'name':passwd,
                                                      'password':passwd2})
                    update_one('deploy.pg.user',[('id','=',pg['id'])],{'password_id':pass_id})
                    update_pg_user_passwd(pg['login'],passwd,port=port)

def parse(sys_args,USER=None, GROUP=None, ROOT=None):
    
    import getpass
    current_login=getpass.getuser()
    if ROOT is None:
        ROOT=os.environ['HOME']
    if 'PASS' in os.environ:
        PASS=os.environ['PASS']
    else:
        PASS=None
    if USER is None:
        USER=current_login
    if GROUP is None:
        import grp,pwd
        GROUP=pwd.getpwnam(current_login).pw_name
    hostname=socket.gethostname()
    usage = "usage: python %prog [options] cmd1, cmd2, .. [db1, db2, ...]\n"
    usage += "  Commands: %s \n" % (','.join(exit_commands) )
    parser = optparse.OptionParser(version='0.1', usage=usage)

    group = optparse.OptionGroup(parser, "Login")
    #site[site_name]={}
    #site[site_name]['server_dest']="server_%s"%site_name
    group.add_option("--account",
                     dest='account',
                     help="Default: [%default]",
                     #default='http://golive-ontime.co.uk:8066/'
                     default='jan'
                     )
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

    cmds, dbs = split_args(args)
    ROOT=os.path.join(ROOT, opt.subdir)
    if not os.path.isdir(ROOT):
        os.makedirs(ROOT) #create if it does not exist

    sock_common = xmlrpclib.ServerProxy (opt.apiurl+'xmlrpc/common')

    uid = sock_common.login(opt.dbname, opt.login,opt.passwd)
    sock = xmlrpclib.ServerProxy(opt.apiurl+'xmlrpc/object')
    user_id,host_id=get_user_id(USER, hostname)

    if 1: #repo
        git_ids=git_search()
        bzr_ids=bzr_search()
        clone_ids=git_ids+bzr_ids
    if args and args[0] in ['render','pg']:
        if PASS:
            key=PASS
        else:
            key=getpass.getpass()
        
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
        elif cmd=='push':
            git_push(git_ids)
            bzr_push(bzr_ids)
        elif cmd=='pg':
            cluster_ids = update_clusters(host_id,key)
        elif cmd=='render':
            render(key)

    elif len(args) in [2,3]:
        cmd,cmd2=args
        #import simplecrypt
        #ciphertext = encrypt('password', plaintext)
        #plaintext = decrypt('password', ciphertext)
        if cmd=='encrypt':
            x=encrypt(key,cmd2)
            t=base64.b64encode(x)
            print [t]
            d = base64.decodestring( t )
            print [decrypt(key,d)]
        elif cmd=='export':
            data_export(cmd2)
        elif cmd=='config' and cmd2=='write':
            if PASS:
                key=PASS
            else:
                key=getpass.getpass()
            application_ids=search('deploy.application',[])
            apps = read('deploy.application', application_ids, ['name','repository_ids'] )
            #deploy_ids=search('deploy.deploy',[])
            #deploy_ids = host_filter(deploy_ids,model='deploy.deploy',field='host_id')
            #dps=read('deploy.deploy',deploy_ids,['site_name',
            #                                     'options',
            #                                     'db_password',
            #                                     'admin_password',
            #                                     'application_id'])
            for app in apps:
                app_name=app['name']
                app_id=app['id']
                repository_ids=app['repository_ids']
                #name=d['site_name']
                prod_config=os.path.join(ROOT, 'server7%s.conf'%app_name)
                arg=[('application_id','=',app_id),('user_id','=',user_id)]
                val={'application_id':app_id,
                     'user_id':user_id}
                
                    #'validated_config_file':prod_config,
                    #'validated_server_path':server_path,
                    #'validated_root':ROOT}
                
                deploy_ids=update_one('deploy.deploy',arg, val)
                dps =read('deploy.deploy',[deploy_ids],['site_name',
                                                        'options',
                                                        'db_password',
                                                        'admin_password',
                                                        'application_id'])
                #assert len(deploy_ids)==1
                #print 'DPS', dps, len(dps)
                assert len(dps)==1
                d=dps[0]
                with open(prod_config, 'wb') as cf:
                    print 'writing config: ', prod_config
                    #app_id,app_name=d['application_id']
                    #app_ret=read('deploy.application', [app_id], ['repository_ids'])
                    #assert len(app_ret)==1
                    
                    #repository_ids = app_ret[0]['repository_ids']
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
                        update_one('deploy.repository.clone',arg, {'remote_id':c_id,'local_user_id':user_id, 'validated_addon_path':addon_path} )
                        #write('deploy.repository.clone',[c_id],{'validated_addon_path':addon_path})

                    c_id,server_path=get_server(repository_ids)
                    arg=[('application_id','=',app_id),('user_id','=',user_id)]
                    val={#'name': app_name,
                         'application_id':app_id,
                         'user_id':user_id,
                         'validated_config_file':prod_config,
                         'validated_server_path':server_path,
                         'validated_root':ROOT}
                    #print val
                    update_one('deploy.deploy',arg, val)
        elif cmd=='config' and cmd2=='show':
            deploy_ids=search('deploy.deploy',[])
            deploy_ids = host_filter(deploy_ids,model='deploy.deploy',field='host_id')
            dps=read('deploy.deploy',deploy_ids,['site_name',
                                                 'options',
                                                 'db_password',
                                                 'admin_password',
                                                 'repository_ids',
                                                 'validated_config_file',
                                                 'validated_server_path',
                                                 ])
            for d in dps:
                print 44*'__'
                print "%s/openerp-server -c %s"%( d['validated_server_path'],d['validated_config_file'] )
                print 'Addon paths:'
                repository_ids = d['repository_ids']
                clones=read('deploy.repository.clone',repository_ids,['validated_addon_path','name',
                                                                      'local_location'])
                for c in clones:
                    print c['name'], c['validated_addon_path']

    return
    for site in sites:
        if site['hostname']==socket.gethostname()  and current_login==site['login']:
            LP=site['sw']['LP']
            GIT=site['sw']['GIT']
            OPTIONS=site['options']
            ServerName=site['ServerName']
            ServerAlias=site.get('ServerAlias',False)
            site_name=site['site_name']
            if not ServerName:
                ServerName=name
            name=hostname+'_'+site_name
            prod_config=os.path.join(ROOT, 'server7%s.conf'%name)
            git_addons=git_branch(ROOT, GIT, subdir='github', branch=False)
            bzr_addons=bzr_branch(ROOT, LP, branch=False)
            wsgi_fn = os.path.join(ROOT, '%s_wsgi.py'%name )
            daemon_fn = '/etc/init.d/%s'%name
            vhost_fn = '/etc/apache2/sites-available/%s.conf'%name
            nvh='/etc/apache2/conf.d/namevhosts_%s' % name
            sn='/etc/apache2/conf.d/servername'
            generated_files = [wsgi_fn, daemon_fn, vhost_fn, nvh, prod_config]
            wsgi_server_log_file =os.path.join(ROOT, 'server_wsgi_%s.log'%site_name)
            conf, server_path = generate_config(bzr_addons+git_addons, prod_config , options=OPTIONS)
            #usage += "  Current config path: %s\n" % prod_config
            #usage += "  Current server path: %s\n" % server_path
            #usage += "Generated files:\n  " + '\n  '.join(generated_files)

            group = optparse.OptionGroup(parser, "Site [%s]"%site_name)
            site[site_name]={}
            site[site_name]['server_dest']="server_%s"%site_name
            group.add_option("--server-%s"%site_name,
                             dest=site[site_name]['server_dest'],
                             help="Specify the OpenERP path with the openerp server module [%default]",
                             default=server_path
                             )
            site[site_name]['config_dest']="config_%s"%site_name
            group.add_option("--config-%s"%site_name,
                             dest=site[site_name]['config_dest'],
                             help="Specify OpenERP Config file [%default]",
                             default=prod_config)
            site[site_name]['wsgi_dest']="wsgi_%s"%site_name
            group.add_option("--wsgi-%s"%site_name,
                             dest=site[site_name]['wsgi_dest'],
                             help="Wsgi file [%default]",
                             default=wsgi_fn)
            site[site_name]['daemon_dest']="daemon_%s"%site_name
            group.add_option("--daemon-%s"%site_name,
                             dest=site[site_name]['daemon_dest'],
                             help="Daemon file [%default]",
                             default=daemon_fn)
            site[site_name]['vhost_dest']="vhost_%s"%site_name
            group.add_option("--vhost-%s"%site_name,
                             dest=site[site_name]['vhost_dest'],
                             help="VHOST file [%default]",
                             default=vhost_fn)
            site[site_name]['nvh_dest']="nvh_%s"%site_name
            group.add_option("--nvh-%s"%site_name,
                             dest=site[site_name]['nvh_dest'],
                             help="vnh file [%default]",
                             default=nvh)       
            parser.add_option_group(group)
    nvh={}
    #print opt.__dict__
    config=[]
    for site in sites:
        if site['hostname']==socket.gethostname() and current_login==site['login']:
            import pprint
            LP=site['sw']['LP']
            GIT=site['sw']['GIT']
            IP=site['IP']
            OPTIONS=site['options']
            PORT=site['PORT']
            SSLCertificateFile=site['SSLCertificateFile']
            SSLCertificateKeyFile=site['SSLCertificateKeyFile']
            SSLCACertificateFile=site.get('SSLCACertificateFile')
            Redirect=site.get('Redirect')
            ProxyPass=site.get('ProxyPass')
            ssl=site['ssl']      
            ServerName=site['ServerName']
            site_name=site['site_name']
            if site['vhost']:
                v=nvh.setdefault( (IP,PORT), [] )
                v.append(site_name)
            wsgi_server_log_file =os.path.join(ROOT, 'server_wsgi_%s.log'%site_name)

            for dest in ['server_dest','config_dest','wsgi_dest','daemon_dest','vhost_dest','nvh_dest']:
                site_dest=site[site_name][dest]
                fn=opt.__dict__[site_dest]
                #print fn
                site[site_name][dest]=fn
            if site['parse_config']:
                config.append(site[site_name]['config_dest'])
                sys.path.append(site[site_name]['server_dest'])
            for command in cmds:
                if command=='show':
                    for dest in ['config_dest','wsgi_dest','daemon_dest','vhost_dest']:
                        fn=site[site_name][dest]
                        if fn is None:
                            fn=''
                        print "%s %s" %(os.path.isfile(fn), fn)
                if command=='status':
                    git_addons=git_status(ROOT, GIT, subdir='github')
                    bzr_addons=bzr_status(ROOT, LP)
                if command=='push':
                    git_addons=git_push(ROOT, GIT, subdir='github')
                    bzr_addons=bzr_push(ROOT, LP)
                if command=='pull':
                    git_addons=git_pull(ROOT, GIT, subdir='github')
                    bzr_addons=bzr_pull(ROOT, LP)
                if command=='write':
                    git_addons=git_branch(ROOT, GIT, subdir='github', branch=False)
                    bzr_addons=bzr_branch(ROOT, LP, branch=False)
                    conf, server_path = generate_config(bzr_addons+git_addons,site[site_name]['config_dest'] , options=OPTIONS)
                    with open(site[site_name]['config_dest'], 'wb') as cf:
                        print 'writing config: ', site[site_name]['config_dest']
                        conf.write(cf)
                    if site['daemon']:
                        print 'writing daemon', site[site_name]['daemon_dest']
                        file(site[site_name]['daemon_dest'],'wb').write( get_daemon(site[site_name]['server_dest'], site[site_name]['config_dest'], USER=USER,GROUP=GROUP,ROOT=ROOT)  )
                        subprocess.call( ("chmod +x %s"%site[site_name]['daemon_dest']).split() )
                    if site['vhost']:
                        print 'writing vhost files for: ', site[site_name]
                        file(site[site_name]['wsgi_dest'],'wb').write( get_wsgi(site[site_name]['config_dest']) )
                        vhost = get_vhost(site_name, site[site_name]['server_dest'], ServerName, site[site_name]['wsgi_dest'] , 
                                          IP=IP, PORT=PORT,SSLCertificateFile=SSLCertificateFile, 
                                          SSLCertificateKeyFile=SSLCertificateKeyFile, SSLCACertificateFile=SSLCACertificateFile,
                                          ProxyPass=ProxyPass,
                                          Redirect=Redirect,
                                          ssl=ssl, USER=USER,GROUP=GROUP,ROOT=ROOT)       
                        file(site[site_name]['vhost_dest'],'wb').write( vhost )

                    #for fn in generated_files:
                    #    print 50*'_'  ,fn, 50*'_'
                    #    print file(fn).read()
                    #sys.exit(0)
                if command=='branch':
                    git_addons=git_branch(ROOT, GIT, subdir='github', branch=True)
                    bzr_addons=bzr_branch(ROOT, LP, branch=True)
                    #conf, server_path = generate_config(bzr_addons+git_addons,site[site_name]['config_dest'] , options=OPTIONS)
                if command=='db':
                    create_or_update_db_user(OPTIONS)
                if command=='unlink':
                    for fn in [site[site_name]['wsgi_dest'], site[site_name]['daemon_dest'], site[site_name]['vhost_dest'], site[site_name]['nvh_dest'], site[site_name]['config_dest']]:
                        try:
                            os.unlink(fn)
                            print 'Removed: ', fn
                        except:
                            print 'can not unlink ', fn
                #print command,exit_commands
    #print 'nvh: ',nvh
    for command in cmds:
        if command == 'write':
            k_out=''
            for k,v in nvh.items():
                k_out+='NameVirtualHost %s:%s\n'%k
            if nvh:
                print 'Updating', sn
                file(sn, 'wb').write('ServerName %s\n'%socket.gethostname())
                nvh='/etc/apache2/conf.d/namevhosts'
                print 'Updating', nvh
                file(nvh, 'wb').write(k_out)

    if set(exit_commands).intersection(cmds):
        sys.exit(0)
    if len(config)==1:
        return opt,args,parser,cmds,dbs,config[0]
    else:
        #assert len(config)==1
        if config:
            print "There are multiple config files for your host available: "
            for i,c in enumerate(config):
                print "  %d) %s" % (i,c)
            user=raw_input('Please select:')
            return opt,args,parser,cmds,dbs,config[ int(user) ]
        else:
            print 'No config to use on your host'
        
    
def get_sites():
    import gtc_sites
    return gtc_sites.sites
#sudo install gtc.py /usr/local/lib/python2.7/dist-packages

if __name__ == '__main__':
    #opt,args,parser,cmds,dbs,config = parse(sys.argv[1:], get_sites() )
    parse(sys.argv[1:])
