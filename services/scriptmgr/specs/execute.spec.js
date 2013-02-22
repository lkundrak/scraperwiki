var utils = require('utils'),
    path = require('path'),
    exec = require('child_process').exec;
var dir = '/tmp/foo/'
describe("Utils cleanup", function() {
  it("deletes files", function() {
      utils.setup_logging('/dev/null', 0);
      // Create files & directories
      exec('mkdir -p '+dir+'wooo; >'+dir+'bar', runs(function(){
          utils.cleanup(dir);
          expect(path.existsSync(dir)).toBeTruthy();
          expect(path.existsSync(dir+'bar')).toBeFalsy();
          expect(path.existsSync(dir+'wooo')).toBeFalsy();
      }));
  });
});
