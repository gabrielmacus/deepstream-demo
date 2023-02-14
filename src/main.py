import gi
gi.require_version('Gst', '1.0')
from gi.repository import GLib, Gst, GObject
from common.is_aarch_64 import is_aarch64
from common.bus_call import bus_call
import pyds
import configparser
import math
import numpy as np

video_analysis_width = 1280
video_analysis_height = 720
video_frame_rate = 60
videos = [
    'file:///home/deepstream_demo/app/videos/example.mp4',
    'file:///home/deepstream_demo/app/videos/example-2.mp4',
    'file:///home/deepstream_demo/app/videos/example-3.mp4',
    'file:///home/deepstream_demo/app/videos/example-4.mp4',
    'file:///home/deepstream_demo/app/videos/example-5.mp4',
    'file:///home/deepstream_demo/app/videos/example-6.mp4',
    ]

def on_pad_added(src, new_pad,source_bin):
        #new_pad.get_current_caps().get_structure(0).get_value("format")
        name = new_pad.get_current_caps().get_structure(0).get_name()
        if name == "video/x-raw":
            bin_ghost_pad = source_bin.get_static_pad("src")
            bin_ghost_pad.set_target(new_pad)

def on_buffer(pad, info, u_data):
        gst_buffer = info.get_buffer()
        if not gst_buffer:
            return
        batch_meta = pyds.gst_buffer_get_nvds_batch_meta(hash(gst_buffer))
        l_frame = batch_meta.frame_meta_list
        while l_frame is not None:
            try:
                #https://docs.nvidia.com/metropolis/deepstream/python-api/PYTHON_API/NvDsMeta/NvDsFrameMeta.html
                frame_meta = pyds.NvDsFrameMeta.cast(l_frame.data)
                #print(frame_meta.buf_pts) Usar para calcular en que segmento estoy
            except StopIteration:
                break
            
            frame = pyds.get_nvds_buf_surface(hash(gst_buffer), frame_meta.batch_id)
            frame_copy = np.array(frame, copy=True, order='C')

            #is_first_obj = True
            l_obj = frame_meta.obj_meta_list
            while l_obj is not None:
                try:
                    # Casting l_obj.data to pyds.NvDsObjectMeta
                    obj_meta=pyds.NvDsObjectMeta.cast(l_obj.data)
                except StopIteration:
                    break

                #if is_first_obj:
                #    is_first_obj = False
                #frame = pyds.get_nvds_buf_surface(hash(gst_buffer), frame_meta.batch_id)
                #frame_copy = np.array(frame, copy=True, order='C')
                #self.video_streams[frame_meta.source_id].save_into_buffer(frame_copy)
                
                # Extract object level meta data from NvDsAnalyticsObjInfo
                l_user_meta = obj_meta.obj_user_meta_list #Get glist containing NvDsUserMeta objects from given NvDsObjectMeta
                # Extract object level meta data from NvDsAnalyticsObjInfo
                while l_user_meta:
                    try:
                        user_meta = pyds.NvDsUserMeta.cast(l_user_meta.data) #Must cast glist data to NvDsUserMeta object
                        if user_meta.base_meta.meta_type == pyds.nvds_get_user_meta_type("NVIDIA.DSANALYTICSOBJ.USER_META"):             
                            user_meta_data = pyds.NvDsAnalyticsObjInfo.cast(user_meta.user_meta_data) #Must cast user metadata to NvDsAnalyticsObjInfo                            
                    except StopIteration:
                        break
                    
                    #self.perform_analitycs(frame_copy, obj_meta, user_meta_data, frame_meta)
                    #for analityc_config in self.video_streams[frame_meta.source_id].analitycs_configs:
                    #    analityc_config.on_meta(self.video_streams[frame_meta.source_id], frame_copy, obj_meta, user_meta_data, frame_meta)
                        
                    try:
                        l_user_meta = l_user_meta.next
                    except StopIteration:
                        break
                try: 
                    l_obj=l_obj.next
                except StopIteration:
                    break
            try:
                l_frame = l_frame.next
            except StopIteration:
                break
        return Gst.PadProbeReturn.OK

def on_child_added(child_proxy,Object,name,user_data):
        if name.find("decodebin") != -1:
            Object.connect("child-added", on_child_added, user_data)
        if "source" in name:
            source_element = child_proxy.get_by_name("source")
            if source_element.find_property('drop-on-latency') != None:
                Object.set_property("drop-on-latency", True)

if __name__ == '__main__':


    Gst.init(None)
    pipeline = Gst.Pipeline()

    # Streammux
    muxer = Gst.ElementFactory.make("nvstreammux")
    muxer.set_property('width', video_analysis_width)
    muxer.set_property('height', video_analysis_height)
    muxer.set_property('live-source', 0)
    muxer.set_property('batched-push-timeout', int(1000000 / video_frame_rate)) # 4000000
    muxer.set_property('batch-size', len(videos))
    muxer.set_property('sync-inputs', 0)
    pipeline.add(muxer)

    # PGIE
    pgie = Gst.ElementFactory.make("nvinfer")
    pgie.set_property('config-file-path', "./configs/pgie.txt")
    pgie.set_property("batch-size", len(videos))
    pipeline.add(pgie)

    # Tracker
    tracker = Gst.ElementFactory.make("nvtracker", "tracker")
    tracker_config = configparser.ConfigParser()
    tracker_config.read('./configs/tracker.txt')
    tracker_config.sections()
    for key in tracker_config['tracker']:
        if key == 'tracker-width' :
            tracker_width = tracker_config.getint('tracker', key)
            tracker.set_property('tracker-width', tracker_width)
        if key == 'tracker-height' :
            tracker_height = tracker_config.getint('tracker', key)
            tracker.set_property('tracker-height', tracker_height)
        if key == 'gpu-id' :
            tracker_gpu_id = tracker_config.getint('tracker', key)
            tracker.set_property('gpu_id', tracker_gpu_id)
        if key == 'll-lib-file' :
            tracker_ll_lib_file = tracker_config.get('tracker', key)
            tracker.set_property('ll-lib-file', tracker_ll_lib_file)
        #if key == 'll-config-file' :
        #    tracker_ll_config_file = tracker_config.get('tracker', key)
        #    tracker.set_property('ll-config-file', tracker_ll_config_file)
        if key == 'enable-batch-process' :
            tracker_enable_batch_process = tracker_config.getint('tracker', key)
            tracker.set_property('enable_batch_process', tracker_enable_batch_process)
        if key == 'enable-past-frame' :
            tracker_enable_past_frame = tracker_config.getint('tracker', key)
            tracker.set_property('enable_past_frame', tracker_enable_past_frame)
    tracker.set_property('ll-config-file', './config/nvmultitracker_config.yml')
    pipeline.add(tracker)

    # Converter
    converter = Gst.ElementFactory.make("nvvideoconvert")
    pipeline.add(converter)

    # Filter
    filter = Gst.ElementFactory.make("capsfilter")
    filter.set_property("caps", Gst.Caps.from_string("video/x-raw(memory:NVMM), format=RGBA"))
    pipeline.add(filter)

    # Tiler
    tiler = Gst.ElementFactory.make("nvmultistreamtiler")
    tiler_rows = int(math.sqrt(len(videos)))
    tiler_columns = int(math.ceil((1.0 * len(videos)) / tiler_rows))
    tiler.set_property("rows", tiler_rows)
    tiler.set_property("columns", tiler_columns)
    tiler.set_property("width", video_analysis_width)
    tiler.set_property("height", video_analysis_height)
    tiler.get_static_pad("sink").add_probe(Gst.PadProbeType.BUFFER, on_buffer, 0)
    pipeline.add(tiler)

    if not is_aarch64():
        # Use CUDA unified memory in the pipeline so frames
        # can be easily accessed on CPU in Python.
        mem_type = int(pyds.NVBUF_MEM_CUDA_UNIFIED)
        ##muxer.set_property("nvbuf-memory-type", mem_type)
        converter.set_property("nvbuf-memory-type", mem_type)
        tiler.set_property("nvbuf-memory-type", mem_type)

    # Mux streams
    for index in range(len(videos)):
        uri = videos[index]
        source_bin=Gst.Bin.new("source-bin-%02d" %index)
        source = Gst.ElementFactory.make("uridecodebin")
        source.set_property("uri",uri)
        source.connect("pad-added",on_pad_added,source_bin)
        source.connect("child-added",on_child_added,source_bin)
        Gst.Bin.add(source_bin,source)
        source_bin.add_pad(Gst.GhostPad.new_no_target("src",Gst.PadDirection.SRC))
        pipeline.add(source_bin)
        sinkpad = muxer.get_request_pad("sink_%u" %index)
        srcpad=source_bin.get_static_pad("src")
        srcpad.link(sinkpad)

    # OSD
    osd = Gst.ElementFactory.make("nvdsosd")
    pipeline.add(osd)

    # Sink
    sink = Gst.ElementFactory.make("nveglglessink")
    sink.set_property("sync", 0)
    sink.set_property("qos", 0)
    pipeline.add(sink)

    # Linking
    muxer.link(pgie)
    pgie.link(tracker)
    tracker.link(converter)
    converter.link(filter)
    filter.link(tiler)
    tiler.link(osd)
    osd.link(sink)
        
    # Init processing
    loop = GLib.MainLoop()
    bus = pipeline.get_bus()
    bus.add_signal_watch()
    bus.connect("message", bus_call, loop)

    pipeline.set_state(Gst.State.PLAYING)
    try:
        loop.run()
    except:
        #TODO: Log error
        print("ERROR!")
    pipeline.set_state(Gst.State.NULL)