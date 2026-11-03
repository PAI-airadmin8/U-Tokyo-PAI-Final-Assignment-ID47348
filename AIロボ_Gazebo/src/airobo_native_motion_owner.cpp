// Physical AI | Gazebo Transport persistent single-owner joint command bridge
// Commands: SNAP, MOVE <joint> <angle_rad> <tolerance_rad> <max_seconds>, QUIT
#include <ignition/transport/Node.hh>
#include <ignition/msgs/double.pb.h>
#include <ignition/msgs/model.pb.h>
#include <ignition/msgs/pose_v.pb.h>
#include <ignition/msgs/contacts.pb.h>
#include <chrono>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <map>
#include <mutex>
#include <sstream>
#include <string>
#include <thread>
#include <array>
using namespace std::chrono;
using Clock=steady_clock;
struct Telemetry {
  std::mutex mu;
  std::map<std::string,double> q;
  std::map<std::string,std::array<double,3>> poses;
  Clock::time_point joint_at=Clock::now()-seconds(100);
  Clock::time_point pose_at=Clock::now()-seconds(100);
  uint64_t count=0;
  struct Contact {Clock::time_point at=Clock::now()-seconds(100); bool paper=false;bool pedestal=false; double stamp=0; uint64_t count=0;};
  Contact fixed,moving;
};
int main() {
  ignition::transport::Node node;
  Telemetry telemetry;
  std::map<std::string, ignition::transport::Node::Publisher> publishers;
  const std::string base="/ai_robo/native_";
  for (auto name:{"joint1","joint2","joint3","joint4","joint_hand"}) {
    publishers[name]=node.Advertise<ignition::msgs::Double>(base+name+"/cmd_pos");
    if (!publishers[name].Valid()) {std::cerr<<"ADVERTISE_FAILED "<<name<<std::endl;return 3;}
  }
  const bool jointSubscribed=node.Subscribe<ignition::msgs::Model>("/ai_robo/native_joint_state",std::function<void(const ignition::msgs::Model&)>([&](const auto& msg) {
    std::lock_guard<std::mutex> lock(telemetry.mu);
    for (const auto& j:msg.joint()) if(j.has_axis1()) {
      std::string name=j.name();
      const auto prefix=std::string("crane_plus_");
      if(name.rfind(prefix,0)==0)name=name.substr(prefix.size());
      telemetry.q[name]=j.axis1().position();
    }
    telemetry.joint_at=Clock::now();
    ++telemetry.count;
  }));
  const bool poseSubscribed=node.Subscribe<ignition::msgs::Pose_V>("/world/default/pose/info",std::function<void(const ignition::msgs::Pose_V&)>([&](const auto& msg){
    std::lock_guard<std::mutex> lock(telemetry.mu);
    for(const auto& p:msg.pose()){
      if(p.name()=="paper_item"||p.name()=="personal_item"||p.name()=="place_pedestal"||p.name()=="pickup_pedestal"||p.name()=="crane_plus_link4"||p.name()=="crane_plus_link_hand")
       telemetry.poses[p.name()]={p.position().x(),p.position().y(),p.position().z()};
    }
    telemetry.pose_at=Clock::now();
  }));
  auto subscribeContacts=[&](const std::string& topic,Telemetry::Contact& c){
    return node.Subscribe<ignition::msgs::Contacts>(topic,std::function<void(const ignition::msgs::Contacts&)>([&telemetry,&c](const auto& msg) {
      bool paper=false,pedestal=false;
      for(const auto& contact:msg.contact()){
        const auto a=contact.collision1().name();const auto b=contact.collision2().name();
        if(a.find("paper_item::body::solid")!=std::string::npos||b.find("paper_item::body::solid")!=std::string::npos)paper=true;
        if(a.find("pedestal")!=std::string::npos||b.find("pedestal")!=std::string::npos)pedestal=true;
      }
      std::lock_guard<std::mutex> lock(telemetry.mu);
      c.at=Clock::now();c.paper=paper;c.pedestal=pedestal;++c.count;
      if(msg.has_header()&&msg.header().has_stamp())c.stamp=msg.header().stamp().sec()+1e-9*msg.header().stamp().nsec();
    }));
  };
  const bool fixSubscribed=subscribeContacts("/world/default/model/crane_plus/link/crane_plus_link4/sensor/ai_robo_fixed_contact/contact",telemetry.fixed);
  const bool movSubscribed=subscribeContacts("/world/default/model/crane_plus/link/crane_plus_link_hand/sensor/ai_robo_contact/contact",telemetry.moving);
  if (!jointSubscribed || !poseSubscribed || !fixSubscribed || !movSubscribed) {
    std::cerr<<"SUBSCRIBE_FAILED "<<jointSubscribed<<" "<<poseSubscribed<<" "<<fixSubscribed<<" "<<movSubscribed<<std::endl;return 4;
  }
  std::cout<<std::setprecision(12)<<"READY native_persistent=1 joints=5 sensors=2"<<std::endl;
  auto ageMs=[](Clock::time_point p){return duration_cast<milliseconds>(Clock::now()-p).count();};
  std::string line;
  while(std::getline(std::cin,line)){
    std::istringstream input(line);
    std::string cmd;input>>cmd;
    if (cmd=="QUIT") {std::cout<<"BYE"<<std::endl;break;}
    if (cmd=="SNAP"){
      std::lock_guard<std::mutex> lock(telemetry.mu);
      std::cout<<"SNAP";
      for(auto n:{"joint1","joint2","joint3","joint4","joint_hand"})
        std::cout<<" "<<n<<"="<<(telemetry.q.count(n)?telemetry.q[n]:NAN);
      for(auto n:{"paper_item","personal_item","place_pedestal","pickup_pedestal","crane_plus_link4","crane_plus_link_hand"}){
        if(telemetry.poses.count(n)) for(auto i=0;i<3;i++)std::cout<<" "<<n<<"_"<<"xyz"[i]<<"="<<telemetry.poses[n][i];
      }
      std::cout<<" age_joint_ms="<<ageMs(telemetry.joint_at)<<" age_pose_ms="<<ageMs(telemetry.pose_at);
      for(auto spec:{std::pair<std::string,Telemetry::Contact*>("fixed",&telemetry.fixed),{"moving",&telemetry.moving}}){
        auto name=spec.first;auto& c=*spec.second;
        std::cout<<" "<<name<<"_paper="<<c.paper<<" "<<name<<"_pedestal="<<c.pedestal
                 <<" "<<name<<"_age_ms="<<ageMs(c.at)<<" "<<name<<"_stamp="<<c.stamp<<" "<<name<<"_count="<<c.count;
      }
      std::cout<<" controller_joint1_connected="<<publishers["joint1"].HasConnections()
               <<" controller_joint3_connected="<<publishers["joint3"].HasConnections()
               <<" feedback_count="<<telemetry.count<<std::endl;
      continue;
    }
    if(cmd=="GRIP"){
      double target=.35,deadlineSec=12;
      input>>target>>deadlineSec;
      if(!input || target<.1 || target>.6 || deadlineSec<2 || deadlineSec>25){
        std::cout<<"ERROR bad_grip_command"<<std::endl;continue;
      }
      auto &pub=publishers["joint_hand"];
      ignition::msgs::Double goal;goal.set_data(target);
      auto start=Clock::now();
      auto deadline=start+duration_cast<Clock::duration>(duration<double>(deadlineSec));
      bool ok=false;int sent=0, stable=0;
      double jaw=NAN,fixedAge=1e9,movingAge=1e9;
      while(Clock::now()<deadline){
        if(pub.HasConnections() && pub.Publish(goal)) ++sent;
        {
          std::lock_guard<std::mutex> lock(telemetry.mu);
          if(telemetry.q.count("joint_hand"))jaw=telemetry.q["joint_hand"];
          fixedAge=ageMs(telemetry.fixed.at);
          movingAge=ageMs(telemetry.moving.at);
          const bool dual=telemetry.fixed.paper && telemetry.moving.paper
            && !telemetry.fixed.pedestal && !telemetry.moving.pedestal
            && fixedAge<300 && movingAge<300;
          if(dual && std::isfinite(jaw) && jaw>.05) ++stable;
          else stable=0;
          if(stable>=8)ok=true;
        }
        if(ok)break;
        std::this_thread::sleep_for(milliseconds(50));
      }
      if(!ok && std::isfinite(jaw)){
        ignition::msgs::Double hold;hold.set_data(jaw);
        for(int k=0;k<5;k++){pub.Publish(hold);std::this_thread::sleep_for(milliseconds(50));}
      }
      std::cout<<"GRIP_RESULT ok="<<ok<<" jaw="<<jaw<<" published="<<sent
               <<" dual_stable_samples="<<stable<<" fixed_age_ms="<<fixedAge
               <<" moving_age_ms="<<movingAge
               <<" elapsed_sec="<<duration<double>(Clock::now()-start).count()<<std::endl;
      continue;
    }
    if(cmd=="MOVE"){
      std::string name;double target=0,tolerance=.01,deadlineSec=7;
      input>>name>>target>>tolerance>>deadlineSec;
      if(!input||!publishers.count(name)||std::isnan(target)||tolerance<=0||tolerance>.1||deadlineSec<.5||deadlineSec>30){
        std::cout<<"ERROR bad_command"<<std::endl;continue;
      }
      double before=NAN,actual=NAN;uint64_t firstCount=0;
      {
        std::lock_guard<std::mutex> lock(telemetry.mu);
        if(telemetry.q.count(name)) before=telemetry.q[name];
        firstCount=telemetry.count;
      }
      bool ok=false;int sent=0,stable=0;uint64_t lastCount=firstCount;int noConnTicks=0;
      auto start=Clock::now();auto deadline=start+duration_cast<Clock::duration>(duration<double>(deadlineSec));
      ignition::msgs::Double goal;goal.set_data(target);
      while(Clock::now()<deadline){
        if(!publishers[name].HasConnections()){++noConnTicks;std::this_thread::sleep_for(milliseconds(50));continue;}
        if(!publishers[name].Publish(goal)){std::this_thread::sleep_for(milliseconds(50));continue;}
        ++sent;
        {
          std::lock_guard<std::mutex> lock(telemetry.mu);
          if(telemetry.q.count(name))actual=telemetry.q[name];
          if(telemetry.count!=lastCount){
            lastCount=telemetry.count;
            stable=(std::isfinite(actual) && std::abs(actual-target)<=tolerance)?stable+1:0;
            if(stable>=3){ok=true;}
          }
        }
        if(ok)break;
        std::this_thread::sleep_for(milliseconds(50));
      }
      if(!ok) {
        // Hold the actual position on timeout, preventing a stale target being
        // continuously driven after the owner aborts the high-level trajectory.
        if(std::isfinite(actual)){
          ignition::msgs::Double hold;hold.set_data(actual);
          for(int k=0;k<5;k++){publishers[name].Publish(hold);std::this_thread::sleep_for(milliseconds(50));}
        }
      }
      auto elapsed=duration<double>(Clock::now()-start).count();
      std::cout<<"RESULT joint="<<name<<" target="<<target<<" before="<<before<<" actual="<<actual
               <<" error="<<std::abs(actual-target)<<" ok="<<ok<<" published="<<sent
               <<" feedback_delta="<<(lastCount-firstCount)<<" no_connection_ticks="<<noConnTicks
               <<" elapsed_sec="<<elapsed<<" stable_samples="<<stable<<std::endl;
      continue;
    }
    std::cout<<"ERROR unsupported_command"<<std::endl;
  }
  return 0;
}
