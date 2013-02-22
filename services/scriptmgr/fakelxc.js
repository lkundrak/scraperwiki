/*
 *  Same interface as lxc.js, but using ordinary child
 *  processes, instead of LXC VMs.
 */

var path = require('path');
var spawn = require('child_process').spawn;
var util = require( path.join(__dirname, 'utils.js') );

// Libraries for language support.
var extra_path;
var httpproxy;

exports.init = function(start, count, lxc_root_folder, settings) {
    extra_path = settings.extra_path;
    util.log.debug('extra_path ' + extra_path);
    httpproxy = settings.httpproxy;
    util.log.debug('httpproxy ' + httpproxy);
};

exports.code_folder = function(vm) {
    return '/tmp';
};

exports.alloc = function(script) {
    var vm = {
        'name': 'Local PID'
    };
    return vm;
};
 
exports.spawn = function(vm, script) {
    var extension = util.extension_for_language(script.language);
    var tmpfile = path.join(exports.code_folder(vm),
      "script." + extension);

    // Happily, all supported languages can use the same
    // convention for passing args: --opt=foo.
    var args = ['--script=' + tmpfile,
      '--scraper=' + script.scraper_name];

    var exe = './scripts/exec.' + extension
    var environ = util.env_for_language(script.language, extra_path);

    if (script.query) {
        environ['QUERY_STRING'] = script.query;
    }

    if (httpproxy) {
        environ['http_proxy'] = 'http://' + httpproxy;
    }

    util.log.debug(script.scraper_name +
      ' spawning ' + exe + ' args '  + args);
    var child = spawn(exe, args, {env: environ});
    vm.name = 'pid' + child.pid;
    vm.child = child;
    return child;
};

exports.kill = function(vm) {
    if (vm.child) {
        vm.child.kill('SIGKILL');
    }
};

exports.release_vm = function(script_, vm_) {
    // Nothing to do.
};

exports.ip_for_vm = function(vm) {
    return '127.0.0.1';
};
