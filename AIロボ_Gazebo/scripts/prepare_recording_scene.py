"""2026年11月3日の正式録画：Gazebo画面・視点・独立ワールドの事前準備。

専用実験機の既存GUIを停止する処理があるため、通常実行には使用しない。
"""
import os,subprocess,signal,time,math,json,xml.etree.ElementTree as ET,pathlib
from scipy.spatial.transform import Rotation as R
base=pathlib.Path('/home/ubuntu/airobot_ws/pai_airobo_v3_delivery')
out=base/'video';out.mkdir(exist_ok=True)
partition='airobo_official_final_v2_20261103'
E=os.environ.copy();E.update(IGN_PARTITION=partition,ROS_DOMAIN_ID='84',DISPLAY=':97',LIBGL_ALWAYS_SOFTWARE='1',QT_QPA_PLATFORM='xcb',XDG_RUNTIME_DIR='/tmp/ai_robo_gui_runtime',IGN_GAZEBO_RESOURCE_PATH='/home/ubuntu/airobot_ws/install/crane_plus_description/share',IGN_GAZEBO_SYSTEM_PLUGIN_PATH='/usr/lib/x86_64-linux-gnu/ign-gazebo-6/plugins')
def cmd(a,t=9):return subprocess.run(a,env=E,capture_output=True,text=True,timeout=t)
t=ET.parse(str(base/'worlds'/'base_no_detach.sdf'));w=t.getroot().find('world')
paper=next(x for x in w.findall('model') if x.get('name')=='paper_item')
paper.find('pose').text='.6 .2 1.025 0 0 0'
pad=ET.parse(str(base/'worlds'/'place_pedestal.sdf')).getroot().find('model');w.append(pad)
p=out/'gazebo_prewarm_final_v2_20261103.sdf'
ET.indent(t,space='  ');t.write(str(p),encoding='utf-8',xml_declaration=True)
ps=cmd(['ps','-eo','pid,args']).stdout.splitlines()
for line in ps:
 if ('ign gazebo -g -v 2' in line or ('mpv --no-config' in line and 'PickPlace' in line)) and 'ps -eo' not in line:
  pid=int(line.strip().split()[0])
  try:os.kill(pid,signal.SIGTERM);print('STOP_GUI_OR_PLAYER',pid,flush=True)
  except Exception as exc:print('WARN',str(exc),flush=True)
time.sleep(2)
slog=open(out/'prewarm_server.log','w')
server=subprocess.Popen(['ign','gazebo','-s','-r','-v','2',str(p)],env=E,stdout=slog,stderr=subprocess.STDOUT,start_new_session=True)
print('PREWARM_SERVER',server.pid,flush=True)
ready=False
for i in range(40):
 if server.poll() is not None:break
 try:
  info=cmd(['ign','topic','-i','-t','/ai_robo/native_joint_state'],8)
  if 'ignition.msgs.Model' in info.stdout:ready=True;break
 except Exception as e:print('DISCOVERY_WARN',e,flush=True)
 time.sleep(.4)
print('SERVER_READY',ready,flush=True)
if not ready:raise RuntimeError('PREWARM_SERVER_NO_STATES')
glog=open(out/'prewarm_gui.log','w')
gui=subprocess.Popen(['ign','gazebo','-g','-v','2'],env=E,stdout=glog,stderr=subprocess.STDOUT,start_new_session=True)
print('GUI_PID',gui.pid,flush=True)
focused=False
for i in range(40):
 info=cmd(['ign','service','-i','-s','/gui/move_to/pose'],8)
 if 'ignition.msgs.GUICamera' in info.stdout:
  pos=(-.22,-.36,1.40);look=(.115,-.07,1.18)
  dx,dy,dz=(look[j]-pos[j] for j in range(3))
  yaw=math.atan2(dy,dx);pitch=math.atan2(-dz,math.hypot(dx,dy))
  x,y,z,ww=R.from_euler('xyz',[0,pitch,yaw]).as_quat()
  req='pose { position { x: %.6f y: %.6f z: %.6f } orientation { x: %.8f y: %.8f z: %.8f w: %.8f } }'%(*pos,x,y,z,ww)
  call=cmd(['ign','service','-s','/gui/move_to/pose','--reqtype','ignition.msgs.GUICamera','--reptype','ignition.msgs.Boolean','--timeout','6000','-r',req],9)
  if 'data: true' in call.stdout:
   focused=True;break
 time.sleep(.5)
print('GUI_FOCUSED',focused,flush=True)
time.sleep(3)
cap=cmd(['import','-window','root',str(out/'prewarm_screenshot_v2.png')],12)
print('SCREENSHOT',cap.returncode,(out/'prewarm_screenshot_v2.png').stat().st_size if (out/'prewarm_screenshot_v2.png').exists() else None,flush=True)
(out/'prewarm_manifest_v2.json').write_text(json.dumps({'partition':partition,'world':str(p),'server_pid':server.pid,'gui_pid':gui.pid,'server_ready':ready,'gui_focused':focused},indent=2))
