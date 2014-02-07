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

if socket.gethostname() in ['asus','jetel']:
    db_user='jan'
    db_password=''
    DEFAULT_USER='jan'
    DEFAULT_GROUP='jan'
    DEFAULT_ROOT='/home/openerp'
else:
    db_user='openerp'
    db_password='openerp'   
    DEFAULT_USER='openerp'
    DEFAULT_GROUP='users'
    DEFAULT_ROOT='/opt/openerp'

def generate_config(addons, fn='server7devel.conf', options=None):
    c=ConfigParser.RawConfigParser()
    cfn=os.path.join(fn)
    server_path=None
    spcnt=0 #allow only one server path
    #if os.path.isfile(cfn):       
    #pass#    c.read(cfn)
    #else:
    if 1:
        c.add_section('options')
        if options is None:
            options=DEFAULT_OPTIONS
        #c.set('options', 'db_host','127.0.0.1')
        for o,v in options:
            c.set('options', o,v)
    addons_path=[]
    for a in addons:
        if os.path.isdir(a):
            server=os.path.join(a,'openerp/addons/base')
            web=os.path.join(a, 'addons/web')
            add=os.path.join(a, 'addons')
            if os.path.isdir(server):
                server_path=a
                spcnt+=1
                if spcnt>1:
                    raise ValueError("only one server path allowed")
            elif os.path.isdir(web) or os.path.isdir(add):
                addons_path.append(os.path.join(a,'addons'))
            else:
                addons_path.append(a)
    c.set('options', 'addons_path', ','.join(addons_path) )
    return c, server_path

#def vcs_status(ROOT, 
def git_remote2local(ROOT, rb, subdir='github'):
    rb, branch,addon_subdir,is_module_path = rb
    l=os.path.join(ROOT, subdir, *rb.split('/')[-2:])
    p=os.path.join(ROOT,subdir, *rb.split('/')[-2:-1]) #parent path
    if is_module_path:
        addon=l
    else:
        addon = os.path.join(l,addon_subdir)
    #if is_module_path:
        #pp=os.path.join(ROOT,subdir, *rb.split('/')[-2:-1]) #parent path        
    #    out.append(p)
    #else:
        #x=[ROOT, subdir] + rb.split('/')[-2:]
        #ll=os.path.join(*x)
    #    out.append(l)
    pp = os.path.join(p, addon)
    return (l,p,pp) #directory, addon path
def git_status(ROOT, remote_branches,subdir='github'):
    for xxx in remote_branches:
        #rb, branch,addon_subdir,is_module_path = xxx
        local_dir, p, addon_path = git_remote2local(ROOT,xxx,subdir=subdir)
        cwd=os.getcwd()
        if os.path.isdir(local_dir):
            os.chdir(local_dir)
            print 44*'_', 'git', local_dir
            args = ["git","status","--branch"]
            subprocess.call(args)
            os.chdir(cwd)
   
def git_branch(ROOT, remote_branches, cmd='pull', subdir='github', branch=False):
    out=[]
    for xxx in remote_branches:
        rb, branch,addon_subdir,is_module_path = xxx
        local_dir, p, addon_path = git_remote2local(ROOT, xxx, subdir=subdir)
        out.append(addon_path)
        if os.path.isdir(local_dir):
            pass       
        else:
            if not os.path.isdir(local_dir):
                os.makedirs(p) #create if it does not exist
            #print [rb, p, l]
            args = ["git","clone","--branch",branch, rb,local_dir]
            #print "subprocess.call with args: ", args
            if branch:
                ret=subprocess.call(args)
    return out
def bzr_remote2local(ROOT, rb):
    l=os.path.join(ROOT, *rb.split('/')[-2:] )
    p=os.path.join(ROOT, *rb.split('/')[-2:-1] ) #parent path
    return l,p
def bzr_status(ROOT, remote_branches):
    for xxx in remote_branches:
        #rb, branch,addon_subdir,is_module_path = xxx
        local_dir,p  = bzr_remote2local(ROOT,xxx)
        cwd=os.getcwd()
        if os.path.isdir(local_dir):
            os.chdir(local_dir)
            print 44*'_', 'bzr', local_dir
            args = ["bzr","status"]
            subprocess.call(args)
            os.chdir(cwd)

def bzr_branch(ROOT, remote_branches, cmd='', branch=False): #for existing branches, cmd can be push or pull
    out=[]
    for rb in remote_branches:
        #l=os.path.join(ROOT, *rb.split('/')[-2:] )
        #p=os.path.join(ROOT, *rb.split('/')[-2:-1] ) #parent path
        l,p = bzr_remote2local(ROOT,rb)
        out.append(l)
        if os.path.isdir(l):
            #print 'exist'
            pass
            #if cmd in ['pull','push']:
            #    r=Branch.open(rb) #remote branch
            #    b=Branch.open(l)  #local branch
            #    if cmd=='pull':
            #        b.pull(r)
            #    if cmd=='push':
            #        b.push(r)
        else:
            if branch:
                if not os.path.isdir(p):
                    os.makedirs(p) #create if it does not exist
                #print 'does not exist',  [rb, p, l]
                r=Branch.open(rb) #remote branch            
                new=r.bzrdir.sprout(l) #new loca branch
    return out

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

%s

test -x ${DAEMON} || exit 0

set -e

case "${1}" in
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

DAEMON_CONF="""PATH=/sbin:/bin:/usr/sbin:/usr/bin
DAEMON=%(server_path)s/openerp-server
NAME=openerp-server
DESC=openerp-server
CONFIG=%(CONFIG)s
USER=%(user)s
GROUP=%(group)s
OPENERP_LOG=%(ROOT)s/server7daemon.log
"""

def get_daemon(server_path, prod_config, USER=None, GROUP=None, ROOT=None):
    arg = dict(server_path=server_path,
               CONFIG=prod_config,
               user=USER,
               group=GROUP,
               ROOT=ROOT)
    return DAEMON % (DAEMON_CONF % arg)

WSGI_SCRIPT="""import sys
import openerp
openerp.tools.config.parse_config(['--config=%s'])
application = openerp.service.wsgi_server.application
""" 

def get_wsgi(prod_config):
    return WSGI_SCRIPT % (prod_config)

VHOST="""<VirtualHost %(IP)s:%(PORT)s>
        ServerName %(ServerName)s

        #WSGIScriptAlias / %(ROOT)s/pjb_wsgi.py
        WSGIScriptAlias / %(WSGIScriptAlias)s
        WSGIDaemonProcess %(name)s user=%(user)s group=%(group)s processes=%(processes)s python-path=%(python_path)s display-name=%(name)s
        WSGIProcessGroup %(name)s
        <Directory %(python_path)s>
            Order allow,deny
            Allow from all
        </Directory>
        ErrorLog ${APACHE_LOG_DIR}/openerp-%(name)s-error.log
        # Possible values include: debug, info, notice, warn, error, crit,                                                                                                                                         
        # alert, emerg.                                                                                                                                                                                            
        LogLevel debug
        CustomLog ${APACHE_LOG_DIR}/openerp-%(name)s.log combined
</VirtualHost>
"""

VHOST_SSL="""<VirtualHost %(IP)s:%(PORT)s>
        ServerName %(ServerName)s

        SSLEngine on
        #SSLCertificateFile /etc/apache2/ssl/apache.crt
        #SSLCertificateKeyFile /etc/apache2/ssl/apache.key
        SSLCertificateFile %(SSLCertificateFile)s
        SSLCertificateKeyFile %(SSLCertificateKeyFile)s

        #WSGIScriptAlias / %(ROOT)s/pjb_wsgi.py
        #WSGIScriptAlias / %(ROOT)s/projects/analogue_micro/apache.conf.py
        WSGIScriptAlias / %(WSGIScriptAlias)s
        WSGIDaemonProcess %(name)s user=%(user)s group=%(group)s processes=%(processes)s python-path=%(python_path)s display-name=%(name)s
        WSGIProcessGroup %(name)s
        <Directory %(python_path)s>
            Order allow,deny
            Allow from all
        </Directory>
        ErrorLog ${APACHE_LOG_DIR}/openerp-%(name)s-error.log
        # Possible values include: debug, info, notice, warn, error, crit,                                                                                                                                         
        # alert, emerg.                                                                                                                                                                                            
        LogLevel debug
        CustomLog ${APACHE_LOG_DIR}/openerp-%(name)s.log combined
</VirtualHost>
"""

def get_vhost(name, python_path, ServerName, WSGIScriptAlias, IP=None, PORT=None, processes=2, SSLCertificateFile=None, SSLCertificateKeyFile=None, ssl=False, USER=None, GROUP=None, ROOT=None):
    if not IP:
        IP='127.0.0.1'
    if ssl:
        if not PORT:
            PORT='443'
        if SSLCertificateFile and SSLCertificateKeyFile:
            arg = dict(name=name,
                       python_path=python_path, 
                       ServerName=ServerName, 
                       user=USER,
                       group=GROUP,
                       ROOT=ROOT,
                       WSGIScriptAlias=WSGIScriptAlias, 
                       IP=IP, PORT=PORT, 
                       processes=processes,
                       SSLCertificateFile=SSLCertificateFile,
                       SSLCertificateKeyFile=SSLCertificateKeyFile)
        else:
            arg = dict(name=name,
                       python_path=python_path, 
                       ServerName=ServerName, 
                       WSGIScriptAlias=WSGIScriptAlias, 
                       IP=IP, PORT=PORT, 
                       user=USER,
                       group=GROUP,
                       ROOT=ROOT,
                       processes=processes,
                       SSLCertificateFile='/etc/apache2/ssl/apache.crt',
                       SSLCertificateKeyFile='/etc/apache2/ssl/apache.key')
        return VHOST_SSL % arg
    else:
        if not PORT:
            PORT='80'
        arg = dict(name=name,
                   python_path=python_path, 
                   ServerName=ServerName, 
                   user=USER,
                   group=GROUP,
                   ROOT=ROOT,
                   WSGIScriptAlias=WSGIScriptAlias, 
                   IP=IP, PORT=PORT, 
                   processes=processes)
        
        return VHOST % arg

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
    if 0:
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
DEFAULT_OPTIONS=[('db_host', '127.0.0.1'),
                 ('db_port', '5432'),
                 ('db_user', db_user),
                 ('unaccent','True'),
                 ('db_password', db_password),
                 ('xmlrpc_interface','0.0.0.0'),
                 ('admin_passwd',db_password)]


def parse(name, sys_args, LP, GIT, OPTIONS=None, ServerName=None, IP='162.13.151.223', PORT='80', SSLCertificateFile=None, SSLCertificateKeyFile=None, ssl=True, ROOT=None, USER=None, GROUP=None):
    hostname=socket.gethostname()
    name=hostname+'_'+name

    if not ROOT:
        ROOT=DEFAULT_ROOT
    if not ServerName:
        ServerName=name
    if not USER:
        USER=DEFAULT_USER
    if not GROUP:
        GROUP=DEFAULT_GROUP
    prod_config=os.path.join(ROOT, 'server7%s.conf'%name)
    git_addons=git_branch(ROOT, GIT, subdir='github', branch=False)
    bzr_addons=bzr_branch(ROOT, LP, branch=False)
    if not OPTIONS:
        OPTIONS=DEFAULT_OPTIONS
    wsgi_fn = os.path.join(ROOT, '%s_wsgi.py'%name )
    daemon_fn = '/etc/init.d/%s'%name
    vhost_fn = '/etc/apache2/sites-available/%s.conf'%name
    nvh='/etc/apache2/conf.d/namevhosts_%s' % name
    sn='/etc/apache2/conf.d/servername'
    generated_files = [wsgi_fn, daemon_fn, vhost_fn, nvh, prod_config]

    conf, server_path = generate_config(bzr_addons+git_addons, prod_config , options=OPTIONS)
    exit_commands=['db','branch','write','status','unlink','push','pull']
    usage = "usage: python %prog [options] command [database_name]\n"
    usage += "  Commands: script,%s \n" % (','.join(exit_commands) )
    usage += "  Current config path: %s\n" % prod_config
    usage += "  Current server path: %s\n" % server_path
    usage += "Generated files:\n  " + '\n  '.join(generated_files)
    parser = optparse.OptionParser(version='0.1', usage=usage)
    group = optparse.OptionGroup(parser, "Common options")
    parser.add_option_group(group)
    
    group.add_option("-s", "--server-pythonpath",
                     dest="server_pythonpath",
                     help="Specify the OpenERP path with the openerp server module [%default]",
                     #default=os.path.join(os.environ['HOME'],'openerp6/server/7.0')
                     #default=os.path.join('../server/70pjb')
                     default=server_path
                     )
    group.add_option("-c", "--config",
                     dest="config",
                     help="Specify OpenERP Config file [%default]",
                     default=prod_config)
    # group.add_option("-d", "--daemon",
    #                  dest="daemon",
    #                  help="Generate write Daemon&apache files to /etc/init.d/openerp,/etc/apache2/sites-available/pjb.conf [%default] (yes|no)",
    #                  default='no')
    # group.add_option("-b", "--branch",
    #                  dest="branch",
    #                  help="branch, generate config and set db user [%default] (yes|no)",
    #                  default='no')
    # group.add_option("--cmd",
    #                  dest="cmd",
    #                  help="cmd to run, [%default] (push|pull)",
    #                  default='')
    # group.add_option("-u", "--unlink",
    #                  dest="unlink",
    #                  help="unlink files [%default] (yes|no)",
    #                  default='no')
    # group.add_option("-t", "--status",
    #                  dest="status",
    #                  help="status [%default] (yes|no)",
    #                  default='no')

    opt, args = parser.parse_args(sys_args)
    generated_files = [wsgi_fn, daemon_fn, vhost_fn, nvh, opt.config]
    dbname=None
    if len(args)==1:
        command = args[0]
    elif len(args)==2:
        command,dbname=args
    else:
        parser.error("Command argument is required.")

    if command=='show':
        for fn in generated_files:
            print "%s %s" %(os.path.isfile(fn), fn)
    if command=='status':
        git_addons=git_status(ROOT, GIT, subdir='github')   
        bzr_addons=bzr_status(ROOT, LP)   
    if command=='write':
        file(daemon_fn,'wb').write( get_daemon(opt.server_pythonpath, opt.config, USER=USER,GROUP=GROUP,ROOT=ROOT)  )
        subprocess.call( ("chmod +x /%s"%daemon_fn).split() )
        file(wsgi_fn,'wb').write( get_wsgi(opt.config) )
        vhost = get_vhost(name, opt.server_pythonpath, ServerName, wsgi_fn , IP=IP, PORT=PORT,SSLCertificateFile=SSLCertificateFile, SSLCertificateKeyFile=SSLCertificateKeyFile, ssl=ssl, USER=USER,GROUP=GROUP,ROOT=ROOT)       
        file(vhost_fn,'wb').write( vhost )        
        if not ssl:
            file(nvh,'wb').write('NameVirtualHost %s:%s\n'%(IP,PORT) )
        file(sn, 'wb').write('ServerName %s\n'%socket.gethostname())
        for fn in generated_files:
            print 50*'_'  ,fn, 50*'_'
            print file(fn).read()
        sys.exit(0)
    if command=='branch':
        git_addons=git_branch(ROOT, GIT, subdir='github', branch=True)
        bzr_addons=bzr_branch(ROOT, LP, branch=True)
        conf, server_path = generate_config(bzr_addons+git_addons,opt.config , options=OPTIONS)
        with open(opt.config, 'wb') as cf:
            conf.write(cf)
    if command=='db':
        create_or_update_db_user(OPTIONS)
    if command=='unlink':
        for fn in [wsgi_fn, daemon_fn, vhost_fn, nvh, opt.config]:
            try:
                os.unlink(fn)
                print 'Removed: ', fn
            except:
                print 'can not unlink ', fn
    #print command,exit_commands
    if command in exit_commands:
        sys.exit(0)
    return opt,args,parser,command,dbname
    
#sudo install gtc.py /usr/local/lib/python2.7/dist-packages
