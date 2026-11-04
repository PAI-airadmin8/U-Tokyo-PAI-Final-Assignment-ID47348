"""2026年11月3日の正式録画：最初の動作指令から退避までを連続撮影する。"""
import os,subprocess,signal,time,json,glob,datetime,pathlib
BASE=pathlib.Path('/home/ubuntu/airobot_ws/pai_airobo_v3_delivery')
OUT=BASE/'video'
E=os.environ.copy();E.update(IGN_PARTITION='airobo_official_final_v2_20261103',AIROBO_PARTITION='airobo_official_final_v2_20261103',AIROBO_EXTERNAL_WORLD='1',ROS_DOMAIN_ID='84',DISPLAY=':97',LIBGL_ALWAYS_SOFTWARE='1',QT_QPA_PLATFORM='xcb',XDG_RUNTIME_DIR='/tmp/ai_robo_gui_runtime',IGN_GAZEBO_RESOURCE_PATH='/home/ubuntu/airobot_ws/install/crane_plus_description/share')
video=OUT/'AIrobo_V3_Official_FINAL_Continuous_20261103.mp4'
logpath=OUT/'official_v2_live.log'
filmlog=OUT/'official_v2_ffmpeg.log'
before=set(glob.glob(str(BASE/'runs'/'qa_*.json')))
# 一回の連続録画。フレームの切り貼りや再生速度変更は行わない。
record=subprocess.Popen(['ffmpeg','-hide_banner','-loglevel','warning','-y','-f','x11grab','-framerate','12','-draw_mouse','0','-video_size','1145x669','-i',':97.0+0,0','-vf','crop=727:550:0:100,scale=1280:720:flags=lanczos,drawtext=text=AIrobo_V3_Real_Physics_Continuous:x=20:y=20:fontsize=23:fontcolor=white:box=1:boxcolor=black@0.55:boxborderw=9','-c:v','libx264','-preset','ultrafast','-crf','23','-pix_fmt','yuv420p','-movflags','+faststart',str(video)],env=E,stdout=subprocess.DEVNULL,stderr=open(filmlog,'w'),start_new_session=True)
time.sleep(1)
running=subprocess.Popen(['python3','-u',str(BASE/'autonomous_pick_place.py')],env=E,stdout=open(logpath,'w',buffering=1),stderr=subprocess.STDOUT,start_new_session=True)
print('RECORD_PID',record.pid,'RUN_PID',running.pid,flush=True)
try:rc=running.wait(timeout=180)
except subprocess.TimeoutExpired:
 rc=124;running.terminate()
print('RUN_EXIT',rc,flush=True)
time.sleep(3)
record.send_signal(signal.SIGINT)
try:record.wait(timeout=15)
except:record.terminate();record.wait(timeout=7)
print('VIDEO_EXIT',record.returncode,flush=True)
fresh=sorted(set(glob.glob(str(BASE/'runs'/'qa_*.json')))-before)
qa=fresh[-1] if fresh else None
data=json.load(open(qa)) if qa else {}
probe=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration,size:stream=codec_name,width,height,nb_frames','-of','json',str(video)],capture_output=True,text=True,timeout=10)
metadata=json.loads(probe.stdout) if probe.returncode==0 else {}
manifest={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'video':str(video),'qa_file':qa,'run_exit':rc,'qa_pass':data.get('pass',False),'summary':data.get('summary'),'video_probe':metadata,'continuous_original':True,'only_initial_pose_reset':True,'pass':rc==0 and data.get('pass') is True and float(metadata.get('format',{}).get('duration',0))>30}
(OUT/'official_v2_manifest.json').write_text(json.dumps(manifest,indent=2))
print('OFFICIAL_RECORD_RESULT',json.dumps(manifest),flush=True)
