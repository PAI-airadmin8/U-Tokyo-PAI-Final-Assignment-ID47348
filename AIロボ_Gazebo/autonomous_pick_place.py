#!/usr/bin/env python3
"""AIロボ V3: one-entrypoint, one motion owner, fully feedback-gated physical Pick & Place."""
import os,sys,json,time,math,subprocess,select,datetime,xml.etree.ElementTree as ET,fcntl
from pathlib import Path
BASE=Path(__file__).resolve().parent
RUN_ID=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S')
PARTITION=os.environ.get('AIROBO_PARTITION','airobo_auto_'+RUN_ID)
E=os.environ.copy()
E.update(IGN_PARTITION=PARTITION,ROS_DOMAIN_ID='84',
 IGN_GAZEBO_RESOURCE_PATH='/home/ubuntu/airobot_ws/install/crane_plus_description/share',
 IGN_GAZEBO_SYSTEM_PLUGIN_PATH='/usr/lib/x86_64-linux-gnu/ign-gazebo-6/plugins')
ROOT=str(BASE/'runs')
Path(ROOT).mkdir(parents=True,exist_ok=True)
WORLD=f'{ROOT}/world_{RUN_ID}.sdf'
LOG=f'{ROOT}/run_{RUN_ID}.log'
RESULT=f'{ROOT}/qa_{RUN_ID}.json'
SERVER_LOG=f'{ROOT}/gazebo_{RUN_ID}.log'
BRIDGE_LOG=f'{ROOT}/bridge_{RUN_ID}.log'
NATIVE=str(BASE/'bin'/'airobo_native_motion_owner')
now=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat()
def die(msg):raise RuntimeError(msg)
def verify(ok,reason):
 if not ok:die(reason)
def vec(p):return [p.get(k,0.) for k in 'xyz']
def distance(a,b):return math.dist(vec(a),vec(b))
def parse(line):
 out={}
 for field in line.split()[1:]:
  if '=' not in field:continue
  k,v=field.split('=',1)
  try:out[k]=float(v)
  except:out[k]=v
 return out
class Bridge:
 def __init__(self):
  self.proc=subprocess.Popen([NATIVE],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=open(BRIDGE_LOG,'w'),env=E,text=True,bufsize=1)
  print('BRIDGE',self._read(12),flush=True)
 def _read(self,seconds):
  r,_,_=select.select([self.proc.stdout],[],[],seconds)
  if not r:die('NATIVE_BRIDGE_TIMED_OUT')
  s=self.proc.stdout.readline().strip()
  if not s:die('NATIVE_BRIDGE_EXITED')
  return s
 def call(self,command,seconds=20):
  if self.proc.poll() is not None:die('NATIVE_BRIDGE_EXITED')
  self.proc.stdin.write(command+'\n');self.proc.stdin.flush()
  s=self._read(seconds)
  if s.startswith('ERROR'):die(s)
  return parse(s)
 def snap(self):
  s=self.call('SNAP',10)
  if s.get('age_joint_ms',1e6)>2500 or s.get('age_pose_ms',1e6)>2500:die('STALE_SIM_TELEMETRY')
  return s
 def move(self,j,target,tol=.012,seconds=9):
  attempts=[]
  for n in range(2):
   ans=self.call(f'MOVE {j} {target:.12f} {tol:.6f} {seconds}',seconds+8)
   attempts.append(ans)
   if ans.get('ok')==1.0:break
  if attempts[-1].get('ok')!=1.0:die(f'JOINT_NOT_REACHED {j} {target} actual={attempts[-1].get("actual")}')
  return {'joint':j,'target':target,'attempts':attempts,'actual':attempts[-1].get('actual')}
 def grip(self,target=.35,seconds=16):
  ans=self.call(f'GRIP {target} {seconds}',seconds+8)
  if ans.get('ok')!=1.0:die(f'GRIP_CONTACT_NOT_STABLE {ans}')
  return ans
 def close(self):
  try:self.call('QUIT',2)
  except:pass
  try:self.proc.terminate()
  except:pass
def pose(s,name):return {k:s[f'{name}_{k}'] for k in 'xyz'}
def dual(s):
 return s.get('fixed_paper')==1.0 and s.get('moving_paper')==1.0 and s.get('fixed_pedestal')==0 and s.get('moving_pedestal')==0 and s.get('fixed_age_ms',1e9)<500 and s.get('moving_age_ms',1e9)<500
def confirm_dual(tag,wait_s=3.0):
 samples=[];good=0
 for k in range(int(wait_s/.20)):
  s=bridge.snap()
  valid=dual(s)
  good=good+1 if valid else 0
  if not valid or k==0:
   samples.append({'k':k,'paper_z':s.get('paper_item_z'),'q2':s.get('joint2'),'q3':s.get('joint3'),'q4':s.get('joint4'),'jaw':s.get('joint_hand'),'fixed_paper':s.get('fixed_paper'),'moving_paper':s.get('moving_paper'),'fixed_pad':s.get('fixed_pedestal'),'moving_pad':s.get('moving_pedestal'),'fixed_age_ms':s.get('fixed_age_ms'),'moving_age_ms':s.get('moving_age_ms')})
  if good>=3:return s
  time.sleep(.20)
 logstage('CONTACT_GATE_FAILURE',{'tag':tag,'samples':samples[-12:]})
 die('DUAL_CONTACT_NOT_STABLE_'+tag)
def release_clear(s):
 return not(s.get('fixed_paper')==1.0 and s.get('fixed_age_ms',1e9)<500) and not(s.get('moving_paper')==1.0 and s.get('moving_age_ms',1e9)<500)
def world_build():
 t=ET.parse(str(BASE/'worlds'/'base_no_detach.sdf'));w=t.getroot().find('world')
 robot=next(x for x in w.findall('model') if x.get('name')=='crane_plus')
 verify(not any('DetachableJoint' in (p.get('name') or '') for p in robot.findall('plugin')),'DETACHABLE_JOINT_NOT_REMOVED')
 paper=next(x for x in w.findall('model') if x.get('name')=='paper_item')
 paper.find('pose').text='0.6 0.2 1.025 0 0 0'
 pad=ET.parse(str(BASE/'worlds'/'place_pedestal.sdf')).getroot().find('model')
 w.append(pad)
 ET.indent(t,space='  ');t.write(WORLD,encoding='utf-8',xml_declaration=True)
def reset_paper():
 req='name: "paper_item" position { x: 0.1134 y: -0.1161 z: 1.1225 } orientation { w: 1 }'
 p=subprocess.run(['ign','service','-s','/world/default/set_pose','--reqtype','ignition.msgs.Pose','--reptype','ignition.msgs.Boolean','--timeout','7000','-r',req],env=E,capture_output=True,text=True,timeout=10)
 verify(p.returncode==0 and 'data: true' in p.stdout,'INITIAL_TARGET_RESET_FAILED')
def logstage(name,data):
 row={'stage':name,'utc':now(),'data':data};report['stages'].append(row)
 print('STAGE',name,json.dumps(data,ensure_ascii=False),flush=True)
 return row
world_build(); Path(BRIDGE_LOG).touch()
report={'started_utc':now(),'partition':PARTITION,'world':WORLD,'single_owner':True,'detachable_joint':False,'stages':[],'pass':False,'abort_reason':None}
lf=open(LOG,'w',buffering=1);sf=open(SERVER_LOG,'w');owner_lock=open(str(BASE/'.onepass_motion_owner.lock'),'w')
server=None;bridge=None
try:
 fcntl.flock(owner_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 server=None if os.environ.get('AIROBO_EXTERNAL_WORLD')=='1' else subprocess.Popen(['ign','gazebo','-s','-r','-v','2',WORLD],env=E,stdout=sf,stderr=subprocess.STDOUT,start_new_session=True)
 time.sleep(1.5)
 bridge=Bridge()
 for _ in range(25):
  try:
   initial=bridge.snap()
   if math.isfinite(initial.get('joint3',math.nan)) and 'paper_item_z' in initial:break
  except RuntimeError:pass
  time.sleep(.4)
 else:die('SIM_NOT_READY')
 initial_paper=pose(initial,'paper_item')
 logstage('ENV_READY',{'q3':initial.get('joint3'),'paper':initial_paper,'topic_conn':initial.get('controller_joint3_connected')})
 # All arm commands through the ONE persistent, acknowledged native bridge.
 preparation=[
  ('joint_hand',-.45),('joint3',-.95),('joint4',.15),
  ('joint2',.34),('joint1',-.653),('joint1',-.8218),
  ('joint2',-.2807),('joint3',-1.5735),('joint4',-.9059)]
 for joint,target in preparation:
  r=bridge.move(joint,target,tol=.020,seconds=11)
  logstage('PREGRASP',r)
 reset_paper()
 time.sleep(1.5)
 s=bridge.snap()
 paper=pose(s,'paper_item')
 verify(distance(paper,dict(x=.1134,y=-.1161,z=1.1225))<.004,'PAPER_RESET_POSITION_DRIFT')
 verify(abs(s['joint3']+1.5735)<.020 and abs(s['joint_hand']+.45)<.020,'PREGRASP_INVALID')
 logstage('PICKUP_READY',{'paper':paper,'joints':{k:s[k] for k in ['joint1','joint2','joint3','joint4','joint_hand']}})
 grip=bridge.grip(.35,16);logstage('GRASP',grip)
 stable=0;last=pose(bridge.snap(),'paper_item')
 for k in range(12):
  time.sleep(.5);s=bridge.snap();p=pose(s,'paper_item')
  diff=distance(p,last)
  stable=stable+1 if dual(s) and s['joint_hand']>.05 and diff<.0005 else 0
  row={'round':k+1,'dual':dual(s),'jaw':s['joint_hand'],'move_mm':diff*1000,'consecutive':stable}
  logstage('GRIP_HOLD',row)
  verify(dual(s),'GRIP_CONTACT_LOST')
  if stable>=3:break
  last=p
 verify(stable>=3,'GRIP_NOT_STABLE')
 grip_pose=pose(s,'paper_item')
 for step,targets in [
  ('LIFT25',[('joint3',-1.55610614269),('joint2',-.27619280924),('joint4',-.91878666658)]),
  ('LIFT50',[('joint3',-1.5387122857),('joint2',-.2716856185),('joint4',-.9316733324)]),
  ('LIFT75',[('joint3',-1.52131842804),('joint2',-.26717842774),('joint4',-.94455999973)]),
  ('LIFT_ATTITUDE',[('joint2',-.26267123699),('joint4',-.97653)])]:
  for j,t in targets:
   r=bridge.move(j,t,tol=.015,seconds=10)
   s=confirm_dual(step+'_'+j)
   logstage(step,{'cmd':r,'paper_z':s['paper_item_z'],'lift_mm':(s['paper_item_z']-grip_pose['z'])*1000})
 for k in range(18):
  before=bridge.snap();z0=before['paper_item_z'];q3=before['joint3']
  r=bridge.move('joint3',q3+.01,tol=.008,seconds=9)
  after=confirm_dual('REAL_LIFT_'+str(k+1))
  rel_change=abs(math.dist(vec(pose(after,'paper_item')),vec(pose(after,'crane_plus_link_hand')))-math.dist(vec(pose(before,'paper_item')),vec(pose(before,'crane_plus_link_hand'))))
  gain=after['paper_item_z']-grip_pose['z']
  logstage('REAL_LIFT',{'step':k+1,'q3':r,'net_z_mm':gain*1000,'delta_z_mm':(after['paper_item_z']-z0)*1000,'relative_gap_change_mm':rel_change*1000,'dual':dual(after)})
  verify(dual(after) and rel_change<.002 and after['paper_item_z']-z0>-.0004,'REAL_LIFT_FAILED')
  if gain>=.005:break
 else:die('LIFT_BELOW_5MM')
 lift_pose=pose(after,'paper_item')
 for i,target in enumerate([-.7218,-.6718,-.6218,-.5718,-.5218,-.4718,-.4218,-.3718,-.3218,-.2718,-.2218],1):
  before=bridge.snap();old=pose(before,'paper_item');oldq=before['joint1']
  r=bridge.move('joint1',target,tol=.012,seconds=10)
  after=confirm_dual('TRANSPORT_'+str(i));p=pose(after,'paper_item')
  dq=after['joint1']-oldq
  ex=old['x']*math.cos(dq)-old['y']*math.sin(dq)
  ey=old['x']*math.sin(dq)+old['y']*math.cos(dq)
  error=math.hypot(p['x']-ex,p['y']-ey)
  valid=dual(after) and error<.002 and old['z']-p['z']<.002
  logstage('TRANSPORT',{'step':i,'q1':r,'xy_err_mm':error*1000,'z_change_mm':(p['z']-old['z'])*1000,'dual':dual(after)})
  verify(valid,'TRANSPORT_CONTACT_OR_TRACKING_FAILED')
 moved=pose(after,'paper_item')
 movedxy=math.hypot(moved['x']-lift_pose['x'],moved['y']-lift_pose['y'])
 verify(movedxy>.080,'TRANSPORT_DISTANCE_FAILED')
 logstage('TRANSPORT_PASS',{'horizontal_mm':movedxy*1000,'paper':moved})
 opened=bridge.move('joint_hand',-.45,tol=.02,seconds=12)
 logstage('RELEASE',opened)
 time.sleep(2)
 s1=bridge.snap();time.sleep(2);s2=bridge.snap()
 cube=pose(s2,'paper_item');pad=pose(s2,'place_pedestal')
 dxy=math.hypot(cube['x']-pad['x'],cube['y']-pad['y'])
 herror=abs(cube['z']-(pad['z']+.0375+.025))
 drift=distance(pose(s1,'paper_item'),cube)
 verify(dxy<.012 and herror<.003 and drift<.0005,'PLACE_GEOMETRY_FAILED')
 logstage('PLACE_ON_PAD',{'paper':cube,'pad':pad,'xy_err_mm':dxy*1000,'z_err_mm':herror*1000,'settle_drift_mm':drift*1000})
 r=bridge.move('joint3',-1.37,tol=.020,seconds=10)
 time.sleep(2);s3=bridge.snap()
 shifted=distance(pose(s3,'paper_item'),cube)
 logstage('RETRACT',{'joint':r,'cube_shift_mm':shifted*1000,'release_clear':release_clear(s3)})
 verify(shifted<.001 and release_clear(s3),'RETRACT_OR_RELEASE_FAILED')
 report['pass']=True
 report['summary']={'real_lift_mm':(lift_pose['z']-grip_pose['z'])*1000,'transport_mm':movedxy*1000,'final_xy_error_mm':dxy*1000,'final_z_error_mm':herror*1000,'final_paper_xyz':cube}
except Exception as ex:
 report['abort_reason']=str(ex)
 print('ABORT',str(ex),flush=True)
finally:
 report['finished_utc']=now()
 Path(RESULT).write_text(json.dumps(report,indent=2,ensure_ascii=False))
 if bridge:bridge.close()
 if server:
  try:server.terminate();server.wait(timeout=7)
  except:server.kill()
 sf.close();lf.close();owner_lock.close()
 print('ONEPASS_FINAL',json.dumps({'pass':report['pass'],'abort_reason':report['abort_reason'],'summary':report.get('summary'),'result_file':RESULT},ensure_ascii=False),flush=True)
if not report['pass']:sys.exit(2)
