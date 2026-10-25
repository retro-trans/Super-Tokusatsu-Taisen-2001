"""Local source-stem and unprompted ASR review; Japanese stays under source/."""
import argparse,hashlib,json,os,subprocess,sys,time
from pathlib import Path
import numpy as np
import soundfile as sf
import sherpa_onnx

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'work/source/movies'
DEST=SOURCE/'song_audit'
FFMPEG='C:/Program Files/ShareX/ffmpeg.exe'


def separate(clip):
    DEST.mkdir(parents=True,exist_ok=True)
    mix=DEST/('movie_%03d_stereo.wav'%clip)
    if not mix.exists():
        subprocess.run([FFMPEG,'-v','error','-y','-f','psxstr','-i',str(SOURCE/('movie_%03d.str'%clip)),
                        '-vn','-ac','2','-ar','44100',str(mix)],check=True)
    vocals=DEST/('movie_%03d_vocals.wav'%clip)
    if not vocals.exists():
        config=sherpa_onnx.OfflineSourceSeparationConfig(model=sherpa_onnx.OfflineSourceSeparationModelConfig(
            uvr=sherpa_onnx.OfflineSourceSeparationUvrModelConfig(model=str(SOURCE/'models/UVR-MDX-NET-Voc_FT.onnx')),
            num_threads=4,provider='cpu'))
        assert config.validate()
        model=sherpa_onnx.OfflineSourceSeparation(config)
        data,rate=sf.read(mix,dtype='float32',always_2d=True)
        start=time.time();result=model.process(sample_rate=rate,samples=np.ascontiguousarray(data.T))
        for stem,name in zip(result.stems,('vocals','instrumental')):
            sf.write(DEST/('movie_%03d_%s.wav'%(clip,name)),stem.data.T,result.sample_rate)
        print('Separated %03d: %.1fs'%(clip,time.time()-start),flush=True)
    return vocals


def main():
    p=argparse.ArgumentParser();p.add_argument('--ids',default='74,71,73');p.add_argument('--separate-only',action='store_true')
    p.add_argument('--model',default='large-v3');p.add_argument('--windows');p.add_argument('--mix',action='store_true');a=p.parse_args()
    ids=list(map(int,a.ids.split(',')))
    paths=[separate(i) for i in ids]
    if a.separate_only:return
    handles=[]
    for lib in (Path(sys.prefix)/'Lib/site-packages/nvidia').glob('*/bin'):
        os.environ['PATH']=str(lib)+os.pathsep+os.environ['PATH'];handles.append(os.add_dll_directory(str(lib)))
    from faster_whisper import WhisperModel
    model_path=SOURCE/'models'/a.model
    model=WhisperModel(str(model_path) if model_path.is_dir() else a.model,device='cuda',compute_type='int8_float16',download_root=str(SOURCE/'models'))
    for clip,path in zip(ids,paths):
        data,rate=sf.read(path,dtype='float32',always_2d=True);mono=data.mean(axis=1)
        # FFmpeg resampling avoids introducing another audio dependency.
        asr=path.with_name(path.stem+'_16k.wav')
        subprocess.run([FFMPEG,'-v','error','-y','-i',str(path),'-ac','1','-ar','16000',str(asr)],check=True)
        samples,_=sf.read(SOURCE/('movie_%03d.wav'%clip) if a.mix else asr,dtype='float32');rows=[]
        windows=[(12,25),(24,32),(30,40),(38,47),(46,55),(53,61),(60,68),(66,76),(82,92),(90,99),(97,106),(104,115)] if clip==74 else [(x,min(x+20,len(samples)/16000)) for x in range(0,int(len(samples)/16000),20)]
        if a.windows:windows=[tuple(map(float,s.split(':'))) for s in a.windows.split(',')]
        for start,end in windows:
            segments,_=model.transcribe(samples[round(start*16000):round(end*16000)],language='ja',beam_size=5,
                temperature=0,condition_on_previous_text=False,vad_filter=False,word_timestamps=True)
            result=[{'start':s.start+start,'end':s.end+start,'jp':s.text,'avg_logprob':s.avg_logprob,
                     'words':[{'start':w.start+start,'end':w.end+start,'jp':w.word,'p':w.probability} for w in s.words or []]} for s in segments]
            rows.append({'window':[start,end],'segments':result})
            print(json.dumps({'id':clip,'window':[start,end],'text':[s['jp'] for s in result]},ensure_ascii=False),flush=True)
        suffix=a.model+('_mix' if a.mix else '_vocals')
        (DEST/('movie_%03d_%s_asr.ja.json'%(clip,suffix))).write_text(json.dumps(rows,ensure_ascii=False,indent=1)+'\n',encoding='utf-8')
    hashes={str(i):hashlib.sha256((SOURCE/('movie_%03d.wav'%i)).read_bytes()).hexdigest() for i in (71,72,73,74)}
    (DEST/'audio_hashes.json').write_text(json.dumps(hashes,indent=1)+'\n')


if __name__=='__main__':main()
