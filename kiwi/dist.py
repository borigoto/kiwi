#
# Kiwi: a Framework and Enhanced Widgets for Python
#
# Copyright (C) 2005 Async Open Source
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307
# USA
#
# Author(s): Johan Dahlin <jdahlin@async.com.br>
#

"""Distutils extensions and utilities"""

from distutils.command.install_lib import install_lib
from distutils.dep_util import newer
from distutils.log import info, warn
from distutils.sysconfig import get_python_lib
from fnmatch import fnmatch
import os
import sys

class TemplateInstallLib(install_lib):
    # Overridable by subclass
    resources = {}
    global_resources = {}
    name = None

    def generate_template(self, resources, global_resources, prefix):
        filename = os.path.join(self.install_dir, self.name,
                                '__installed__.py')
        self.mkpath(os.path.dirname(filename))
        fp = open(filename, 'w')
        fp.write('# Generated by setup.py do not modify\n')
        fp.write('import os\n')
        fp.write('%s\n' % prefix)
        self._write_dictionary(fp, 'resources', resources)
        self._write_dictionary(fp, 'global_resources', global_resources)
        fp.close()

        return filename

    def _write_dictionary(self, fp, name, dictionary):
        fp.write('%s = {}\n' % name)
        for key, value in dictionary.items():
            value = value.replace('$datadir', '$prefix/share/%s' % self.name)
            value = value.replace('$sysconfdir', '$prefix/etc')
            parts = []
            for part in value.split('/'):
                if part == '$prefix':
                    part = 'prefix'
                else:
                    part = '"%s"' % part
                parts.append(part)

            fp.write("%s['%s'] = %s\n" % (
                name, key, 'os.path.join(%s)' % ', '.join(parts)))

    def install(self):
        if not self.name:
            raise TypeError("%r is missing name" % self)

        if 'bdist_wininst' in sys.argv:
            prefix = 'import sys\nprefix = sys.prefix'
        else:
            install = self.distribution.get_command_obj('install')
            prefix = 'prefix = "%s"' % install.prefix

        install = self.distribution.get_command_obj('install')

        template = self.generate_template(self.resources,
                                          self.global_resources,
                                          prefix)
        return install_lib.install(self) + [template]

def get_site_packages_dir(*dirs):
    """
    Gets the relative path of the site-packages directory

    This is mainly useful for setup.py usage:

    >>> setup(...
              data_files=[(get_site_packages_dir('foo'),
                           files..)])

    where files is a list of files to be installed in
    a directory called foo created in your site-packages directory

    @param dirs: directory names to be appended
    """

    libdir = get_python_lib(plat_specific=False,
                            standard_lib=True, prefix='')
    return os.path.join(libdir, 'site-packages', *dirs)

def listfiles(*dirs):
    dir, pattern = os.path.split(os.path.join(*dirs))
    return [os.path.join(dir, filename)
            for filename in os.listdir(os.path.abspath(dir))
                if filename[0] != '.' and fnmatch(filename, pattern)]

def compile_po_files(appname, dirname='locale'):
    if os.system('msgfmt 2> /dev/null') != 256:
        warn('msgfmt is missing, not installing translations')
        return []

    data_files = []
    for po in listfiles('po', '*.po'):
        lang = os.path.basename(po[:-3])
        mo = os.path.join(dirname, lang, 'LC_MESSAGES', appname + '.mo')

        if not os.path.exists(mo) or newer(po, mo):
            directory = os.path.dirname(mo)
            if not os.path.exists(directory):
                info("creating %s" % directory)
                os.makedirs(directory)
            cmd = 'msgfmt -o %s %s' % (mo, po)
            info('compiling %s -> %s' % (po, mo))
            if os.system(cmd) != 0:
                raise SystemExit("Error while running msgfmt")
        dest = os.path.dirname(os.path.join('share', mo))
        data_files.append((dest, [mo]))

    return data_files

def listpackages(root, exclude=None):
    "Recursivly list all packages in directory root"

    packages = []
    if not os.path.isdir(root):
        raise ValueError("root must be a directory")

    if os.path.exists(os.path.join(root, '__init__.py')):
        packages.append(root.replace('/', '.'))

    for filename in os.listdir(root):
        full = os.path.join(root, filename)
        if os.path.isdir(full):
            packages.extend(listpackages(full))

    if exclude:
        for package in packages[:]:
            if package.startswith(exclude):
                packages.remove(package)

    return packages

