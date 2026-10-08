"""Independent short-window Whisper checks; private Japanese output only."""
import json
import os
from pathlib import Path
import sys
import wave
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'work/source/movies'
handles = []
for lib in (Path(sys.prefix) / 'Lib/site-packages/nvidia').glob('*/bin'):
    os.environ['PATH'] = str(lib) + os.pathsep + os.environ['PATH']
    handles.append(os.add_dll_directory(str(lib)))
import numpy as np
from faster_whisper import WhisperModel
model = WhisperModel('large-v3', device='cuda', compute_type='int8_float16',
                     download_root=str(SOURCE / 'models'))
checks = [(74,14,25),(74,24,40),(74,53,61),(74,84,98),
          (5,0,5.8),(6,5,10),(6,10,19),(12,0,3),(19,0,6),
          (27,9,14),(33,0,6),(39,0,8),(43,9,15),(47,0,4)]
rows=[]
for clip,start,end in checks:
    with wave.open(str(SOURCE / ('movie_%03d.wav' % clip))) as wav:
        wav.setpos(round(start*wav.getframerate()))
        samples=np.frombuffer(wav.readframes(round((end-start)*wav.getframerate())),dtype=np.int16).astype(np.float32)/32768
    segs,info=model.transcribe(samples,language='ja',beam_size=5,
        condition_on_previous_text=False,vad_filter=False,word_timestamps=True)
    items=[{'start':s.start+start,'end':s.end+start,'jp':s.text,
            'avg_logprob':s.avg_logprob} for s in segs]
    rows.append({'id':clip,'window':[start,end],'segments':items})
    print(json.dumps(rows[-1],ensure_ascii=False),flush=True)
(SOURCE/'asr_crops.ja.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
