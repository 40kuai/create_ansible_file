#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2018/9/26 下午2:25
# @Author  : 40kuai
# @File    : create_ansible_host.py
# @Software: PyCharm

import ConfigParser
import time
import requests
from aliyun import edas
from pprint import pprint



DEFAULTSECT = "DEFAULT"

class MyConfigParser(ConfigParser.ConfigParser):
    def write(self, fp):
        """Write an .ini-format representation of the configuration state."""
        if self._defaults:
            fp.write("[%s]\n" % DEFAULTSECT)
            for (key, value) in self._defaults.items():
                fp.write("%s=%s\n" % (key, str(value).replace('\n', '\n\t')))
            fp.write("\n")
        for section in self._sections:
            fp.write("[%s]\n" % section)
            for (key, value) in self._sections[section].items():
                if key == "__name__":
                    continue
                if (value is not None) or (self._optcre == self.OPTCRE):
                    key = "=".join((key, str(value).replace('\n', '\n\t')))
                fp.write("%s\n" % (key))
            fp.write("\n")


def config_ini(filename):
    config = MyConfigParser(allow_no_value=True)
    config.read(filename)
    return config


if __name__ == '__main__':
    # appname和appID对应关系
    app_name_id = {}
    # appname和对应服务器IP
    app_name_ip = {}
    # ini文件appname和对应服务器IP
    ini_app_name_ip = {}

    file_name = "/etc/ansible/hosts"
    # 阿里云api获取app和appid对应关系字典
    edas_obj = edas.Edas()
    app_info_list = edas_obj.get_all_appinfo()["ApplicationList"]["Application"]
    for app in app_info_list:
        app_name_id[app["Name"]] = app["AppId"]

    # 读取ansible配置文件
    config = config_ini(file_name)

    # 从阿里云获取ansible中配置的对应app所对应的IP列表
    for appname in config.sections():
        if appname in app_name_id:
            app_info_data = edas_obj.get_host_ip_for_app(app_name_id[appname])
            app_name_ip[appname] = []
            for app_ip in app_info_data["AppInfo"]["EcuList"]["Ecu"]:
                app_name_ip[appname].append(app_ip["IpAddr"])
        else:
            if appname.startswith("prod") and ":" not in appname:
                print appname
                if appname != "prod-im-send-provider":
                    print appname,"error"
                    content = "ansible配置edas名称不存在：%s" % (appname)
                    dingding_alarm(content)

    # 从ini文件获取配置的对应app所对应的IP列表
    for appname in app_name_ip:
        print appname
        ini_app_name_ip[appname] = []
        for i in config.options(appname):
            ini_app_name_ip[appname].append(i.split()[0])

    # 对比
    for appname in app_name_ip:
        new_ip = set(app_name_ip[appname]) - set(ini_app_name_ip[appname])
        old_ip = set(ini_app_name_ip[appname]) - set(app_name_ip[appname])
        if new_ip:
            for ip in new_ip:
                option = "%s ansible_ssh_user" % ip
                config.set(appname, option, "root ansible_ssh_pass='123456'")
                print "add ",appname, option, "root ansible_ssh_pass='123456",time.ctime()
        if old_ip:
            for ip in old_ip:
                option = "%s ansible_ssh_user" % ip
                config.remove_option(appname, option)
                print "del ",appname, option, "root ansible_ssh_pass='123456'",time.ctime()

    config.write(open(file_name, "w"))
