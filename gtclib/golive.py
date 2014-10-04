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

def chown(fn,user,group,options=''): #-R

    if options:
        o=options.split()
    else:
        o=[]
    
    ret=subprocess.call(["chown","%s:%s"%(user,group),fn]+o )
    #print [ret]
    return ret

def write_file(fn,c,user,group):

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


def read(model,ids,fnames):
#    return sock.execute(dbname, uid, 'g77', 'deploy.repository.clone', 'read',  clone_ids,['git_clone','mkdir'])
    #print opt.dbname, uid, opt.passwd, model, 'read',  ids,fnames
    ret =  sock.execute(opt.dbname, uid, opt.passwd, model, 'read',  ids,fnames)
    #print ret
    return ret
def write(model,ids,value):
    ret =  sock.execute(opt.dbname, uid, opt.passwd, model, 'write',  ids,value)
    return ret

def search(model, domain):
    return sock.execute(opt.dbname, uid, opt.passwd, model, 'search', domain)

import socket
import pprint
import resource
import os

def update_shmem(mem_total):
    pass

def run_bash(t_id,r_id,content,subprocess_arg):
    script=os.path.join(os.getcwd(), "script_%d_%d.sh"%(t_id,r_id) )
    file(script,'wb').write(content)
    subprocess.call(["chmod","+x",script])
#print install_script
    print '   executing bash script', script
    arg=eval(subprocess_arg)
    subprocess.call(arg )
    print '   deleting bash script', script
    subprocess.call(["rm",script])

def render():
    hostname=socket.gethostname()

    host_ids=search('deploy.host',[('name','=',hostname)])
    #host_explore(host_ids)

    ret=sock.execute(opt.dbname, uid, opt.passwd, 'deploy.host','render',host_ids)
    for h,model,t_id,r_id,out_file,content,user,group,_type,name,python_function,subprocess_arg,sequence in ret:
        if _type=='template':
            write_file(out_file,content,user,group)
        elif _type=='python' and model=='deploy.host':
            my_code=compile(content, 'mypy', "exec")
            print 'executing python code', [t_id,r_id,python_function]            
            exec my_code
            ret=eval(python_function)
        elif _type=='bash' and model=='deploy.host':            
            run_bash(t_id,r_id,content,subprocess_arg)

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
    items = read('deploy.repository.clone',clone_ids,['url','local_location_fnc'] )
    server_path=None
    spcnt=0 #allow only one server path
    for c in items:
        a=get_local_dir(c) 
        if os.path.isdir(a):
            server=os.path.join(a,'openerp/addons/base')
            #web=os.path.join(a, 'addons/web')
            #add=os.path.join(a, 'addons')
            if os.path.isdir(server):
                server_path=a
                spcnt+=1
                if spcnt>1:
                    raise ValueError("only one server path allowed")

    return server_path
    
def get_addons(clone_ids):
    items = read('deploy.repository.clone',clone_ids,['url','local_location_fnc','addon_subdir'] )
    addons_path=[]
    for c in items:
        a=get_local_dir(c) 
        print 'LOCAL DIR', a
        if os.path.isdir(a):
            web=os.path.join(a, 'addons/web')
            add=os.path.join(a, 'addons')
            if c['addon_subdir']:
                add2=os.path.join(a, c['addon_subdir'] )
            else:
                add2=''

            if os.path.isdir(web) or os.path.isdir(add):
                addons_path.append(os.path.join(a,'addons'))
            elif os.path.isdir(add2):
                addons_path.append(add2)
            else:
                addons_path.append(a)
    return addons_path
def create_odoo_config(options, addons, fn='server7devel.conf', logfile=None):
    c=ConfigParser.RawConfigParser()
    cfn=os.path.join(fn)
    if 1:
        c.add_section('options')
        for o,v in options:
            c.set('options', o,v)
    c.set('options', 'addons_path', ','.join(addons) )
    if logfile is not None:
        c.set('options', 'logfile', logfile)
    return c
def generate_config(clone_ids,options, fn=None, logfile=None):
    addons=get_addons(clone_ids)
    print addons
    c=create_odoo_config(options,addons,fn=fn,logfile=logfile)
    return c
def get_local_dir(item):
    #current_login=getpass.getuser()
    HOME=os.environ['HOME']
    l=item['local_location_fnc']
    if l.startswith('/'):
        return l
    else:
        return os.path.join(HOME,l)

def git_clone(clone_ids):
    items = read('deploy.repository.clone',clone_ids,['url','local_location_fnc','branch'] )
    for c in items:
        #print c['mkdir']
        local_dir=get_local_dir(c)      
        url=c['url']
        branch=c['branch']
        if os.path.isdir(local_dir):
            pass       
        else:
            if not os.path.isdir(local_dir):
                #if create_branch:
                os.makedirs(local_dir) #create if it does not exist
            args = ["git","clone","--branch",branch, url,local_dir]
            ret=subprocess.call(args)
                #return out
def bzr_pull(clone_ids):
    items = read('deploy.repository.clone',clone_ids,['url','local_location_fnc'] )
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

def get_parent_dir(path):
    arg=path.split('/')[-2:-1]
    arg=['/']+path.split('/')[:-1]
    p=os.path.join(*arg )
    #print 'Parent Dir for ', path, arg,p
    return p

def bzr_branch(clone_ids): #for existing branches, cmd can be push or pull
    items = read('deploy.repository.clone',clone_ids,['url','local_location_fnc'] )
    for c in items:
        #print c['mkdir']
        local_dir=get_local_dir(c)                
        url=c['url']
        p=get_parent_dir(local_dir)
        if not os.path.isdir(p):
            os.makedirs(p) #create if it does not exist
            #    #print 'does not exist',  [rb, p, l]
            r=Branch.open(url) #remote branch            
            new=r.bzrdir.sprout(local_dir) #new loca branch
#    return out

#def bzr_branch():
#    items = read('deploy.repository.clone',clone_ids,['url','local_location_fnc'] )
#    for c in items:
#        print "#bzr url,local: %s,%s"%(c['url'], c['local_location_fnc'])
#        local=get_local_dir(c)       

def git_status(clone_ids):
    items = read('deploy.repository.clone',clone_ids,['local_location_fnc'] )
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
    items = read('deploy.repository.clone',clone_ids,['url','local_location_fnc'] )
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
    items = read('deploy.repository.clone',clone_ids,['url','local_location_fnc','branch'] )
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
    items = read('deploy.repository.clone',clone_ids,['url','local_location_fnc'] )
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
    items = read('deploy.repository.clone',clone_ids,['url','local_location_fnc','branch'] )
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
            subprocess.call(args)
            os.chdir(cwd)

DAEMON="""#!/bin/bash

### BEGIN INIT INFO
# Provides:		openerp-server
# Required-Start:	$remote_fs $syslog
# Required-Stop:	$remote_fs $syslog
# Should-Start:		$network
# Should-Stop:		$network
# Default-Start:	2 3 4 5
# Default-Stop:		0 1 6
# Short-Description:	Enterprise Resource Management software
# Description:		Open ERP is a complete ERP and CRM software.
### END INIT INFO

<%
  import os
  PATH="/sbin:/bin:/usr/sbin:/usr/bin"
  DAEMON=os.path.join(server_path, 'openerp-server')
  NAME="openerp-server"
  DESC="openerp-server"
  #CONFIG=${CONFIG}
  USER=user
  GROUP=group
  OPENERP_LOG=os.path.join(ROOT,'server7daemon.log')
%>

test -x ${DAEMON} || exit 0

set -e

case "$${1}" in
	start)
		echo -n "Starting ${DESC}: "

		start-stop-daemon --start --quiet --pidfile /var/run/${NAME}.pid \
			--chuid ${USER} --group ${GROUP} --background --make-pidfile \
			--exec ${DAEMON} -- --config=${CONFIG} --logfile=${OPENERP_LOG}
		echo "${NAME}."
		;;

	stop)
		echo -n "Stopping ${DESC}: "

		start-stop-daemon --stop --quiet --pidfile /var/run/${NAME}.pid \
			--oknodo

		echo "${NAME}."
		;;

	restart|force-reload)
		echo -n "Restarting ${DESC}: "

		start-stop-daemon --stop --quiet --pidfile /var/run/${NAME}.pid \
			--oknodo

		sleep 1

		start-stop-daemon --start --quiet --pidfile /var/run/${NAME}.pid \
			--chuid ${USER} --group ${GROUP} --background --make-pidfile \
			--exec ${DAEMON} -- --config=${CONFIG} --logfile=${OPENERP_LOG}
		echo "${NAME}."
		;;

	*)
		N=/etc/init.d/${NAME}
		echo "Usage: ${NAME} {start|stop|restart|force-reload}" >&2
		exit 1
		;;
esac
exit 0
"""

def get_daemon(server_path, prod_config, USER=None, GROUP=None, ROOT=None):
    arg = dict(server_path=server_path,
               CONFIG=prod_config,
               user=USER,
               group=GROUP,
               ROOT=ROOT)
    return render_mako(DAEMON, arg)

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

exit_commands=['db','branch','write','status','unlink','push','pull', 'show']
def split_args(args):
    cmds=set(args).intersection(set(exit_commands))
    dbs=set(args)-cmds
    return list(cmds), list(dbs)
def git_search():   
    return search('deploy.repository.clone',[('remote_id.type','=','git')] )

def bzr_search():
    return search('deploy.repository.clone',[('remote_id.type','=','bzr')] )
def deploy_search():
    return 

def parse(sys_args,USER=None, GROUP=None, ROOT=None):
    hostname=socket.gethostname()
    import getpass
    current_login=getpass.getuser()
    if ROOT is None:
        ROOT=os.environ['HOME']
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
    if 1: #repo
        git_ids=git_search()
        bzr_ids=bzr_search()
        clone_ids=git_ids+bzr_ids
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
        elif cmd=='render':
            render()
    elif len(args) in [2,3]:
        key=getpass.getpass()
        cmd,cmd2=args
        #import simplecrypt
        from simplecrypt import encrypt, decrypt
        import base64
        #ciphertext = encrypt('password', plaintext)
        #plaintext = decrypt('password', ciphertext)
        if cmd=='config':
            deploy_ids=search('deploy.deploy',[] )
            dps=read('deploy.deploy',deploy_ids,['site_name',
                                                 'options',
                                                 'db_password',
                                                 'admin_password',
                                                 'clone_ids'])
            for d in dps:
                name=d['site_name']
                prod_config=os.path.join(ROOT, 'server7%s.conf'%name)
                with open(prod_config, 'wb') as cf:
                    print 'writing config: ', prod_config
                    clone_ids = d['clone_ids']
                    options=eval(d['options'])
                    db_pass=d['db_password']
                    admin_pass=d['admin_password']
                    
                    db_pass=base64.decodestring(db_pass)
                    admin_pass=base64.decodestring(admin_pass)
                    options.append( ('db_password', decrypt(key,db_pass)) )
                    options.append( ('admin_password', decrypt(key,admin_pass)) )
                    conf=generate_config(clone_ids,options)
                    conf.write(cf)

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
