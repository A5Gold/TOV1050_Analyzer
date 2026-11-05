if(process.versions.electron && process.type==='browser'){
  const Module=require('node:module'),load=Module._load;
  let installed=false;
  Module._load=function(request,...args){
    const value=load.call(this,request,...args);
    if(request==='electron' && value.app && !installed){
      installed=true;
      const path=require('node:path');
      value.app.commandLine.appendSwitch('remote-debugging-port','9238');
      value.app.setPath('userData',path.join(__dirname,'user-data'));
      value.dialog.showOpenDialog=async()=>({canceled:false,filePaths:[path.join(__dirname,'TWL-activation-smoke.csv')]});
    }
    return value;
  };
}
