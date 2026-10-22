"""Run: uvicorn app.main:app --host 0.0.0.0 --port 8000"""
from __future__ import annotations
import json, logging, mimetypes, os, re, shutil, tempfile, threading, time
from collections import defaultdict, deque
from starlette.concurrency import run_in_threadpool
from pathlib import Path
from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.gzip import GZipMiddleware
from .processor import OPS, ProcessingError, process, pdfopen
from .advanced import detect_labeled_fields

ROOT=Path(__file__).resolve().parents[1]
MAX_BYTES=int(os.getenv('MAX_UPLOAD_MB','50'))*1024*1024
MAX_FILES=25
MAX_JOB_BYTES=int(os.getenv('MAX_JOB_MB','120'))*1024*1024
EPHEMERAL_MODE=os.getenv('PDFCRAFT_EPHEMERAL_MODE','false').lower() in ('1','yes','true')
PROCESS_SLOTS=threading.BoundedSemaphore(max(1,min(2,int(os.getenv('PDFCRAFT_CONCURRENT_JOBS','1')))))
MAX_OPTS_BYTES=int(os.getenv('PDFCRAFT_OPTIONS_KB','64'))*1024
RATE_LIMIT=int(os.getenv('PDFCRAFT_REQUESTS_PER_10_MIN','20'))
RATE_EVENTS=defaultdict(deque)
RATE_LOCK=threading.Lock()
app=FastAPI(title='Doclyro API',description='Document conversion tools',version='1.0.0')
app.add_middleware(GZipMiddleware,minimum_size=1000)
logging.basicConfig(level=logging.INFO)

@app.middleware('http')
async def security_headers(request:Request,call_next):
    response=await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='no-referrer'
    response.headers['X-Frame-Options']='DENY'
    response.headers['Permissions-Policy']='camera=(self), microphone=(), geolocation=()'
    response.headers['X-Permitted-Cross-Domain-Policies']='none'
    response.headers['Cache-Control']='no-store'
    return response

@app.exception_handler(ProcessingError)
async def handle_processing_error(request:Request,exc:ProcessingError):
    return JSONResponse(status_code=422,content={'error':str(exc)})

@app.get('/api/health')
def health():
    return {'status':'ok','tools':len(OPS),'max_upload_mb':MAX_BYTES//1048576, 'max_job_mb':MAX_JOB_BYTES//1048576,
            'office_converter':bool(shutil.which('libreoffice')),
            'ocr_engine':bool(shutil.which('tesseract')),
            'ghostscript':bool(shutil.which('gs')),
            'translation_configured':bool(os.getenv('LIBRETRANSLATE_URL')),
            'email_configured':bool(os.getenv('SMTP_HOST') and os.getenv('SMTP_FROM')),
            'secure_url_conversion_enabled':os.getenv('PDFCRAFT_ALLOW_REMOTE_URLS','false').lower() in ('1','yes','true'),
            'ephemeral_mode':EPHEMERAL_MODE}

@app.get('/api/capabilities')
def capabilities():
    return {'name':'Doclyro','version':'1.0.0','tools':len(OPS),
            'persistent_accounts':not EPHEMERAL_MODE,
            'vault':not EPHEMERAL_MODE,'remote_signing':not EPHEMERAL_MODE,
            'cloud_connectors':not EPHEMERAL_MODE,
            'ephemeral_mode':EPHEMERAL_MODE,
            'max_upload_mb':MAX_BYTES//1048576,'max_job_mb':MAX_JOB_BYTES//1048576,
            'note':('Guest-only preview: downloads must be saved locally. Files and accounts are not persisted.'
                    if EPHEMERAL_MODE else 'Persistent storage depends on the host configuration.')}


def limit_request(request:Request):
    '''Best-effort single-instance throttle; reset on app restart.
    Does not trust spoofable client-origin headers.
    '''
    now=time.monotonic()
    client=request.client.host if request.client else 'unknown'
    with RATE_LOCK:
        # Bounded cleanup keeps public preview from growing memory indefinitely.
        if len(RATE_EVENTS)>2000:
            for key in list(RATE_EVENTS):
                if not RATE_EVENTS[key] or RATE_EVENTS[key][-1] < now-600:
                    del RATE_EVENTS[key]
            if len(RATE_EVENTS)>2048 and client not in RATE_EVENTS:
                raise HTTPException(status_code=429,detail='Service is busy; try later.')
        events=RATE_EVENTS[client]
        while events and events[0]<now-600:events.popleft()
        if len(events)>=RATE_LIMIT:
            raise HTTPException(status_code=429,detail='Processing rate limit reached; try later.')
        events.append(now)


@app.get('/api/tools')
def tools():return {'slugs':list(OPS),'total':len(OPS)}

def safe_name(name: str):
    name=Path((name or 'file').replace('\\','/')).name
    name=re.sub(r'[^A-Za-z0-9_. ()-]','_',name)
    return name[:90] or 'file'

async def save_uploads(wd: Path, uploads: list[UploadFile]) -> list[Path]:
    if len(uploads)>MAX_FILES:raise ProcessingError('Too many files in one request.')
    saved=[];total=0
    for i,item in enumerate(uploads):
        if not item.filename:continue
        name=safe_name(item.filename)
        dest=wd/f'{i:02d}_{name}'
        size=0
        with dest.open('wb') as f:
            while True:
                chunk=await item.read(1024*1024)
                if not chunk:break
                size+=len(chunk);total+=len(chunk)
                if total>MAX_JOB_BYTES:raise ProcessingError('Total upload size exceeds the configured job limit.')
                if size>MAX_BYTES:raise ProcessingError(f'File {name} exceeds the {MAX_BYTES//1048576} MB limit.')
                f.write(chunk)
        if not size: raise ProcessingError(f'{name} is empty.')
        saved.append(dest)
    return saved

@app.post('/api/process/{slug}')
async def run_tool(slug:str, background_tasks:BackgroundTasks,request:Request,
                  files:list[UploadFile]|None=File(None),
                  options:str=Form('{}')):
    if slug not in OPS:raise HTTPException(404,'Tool not found')
    limit_request(request)
    if len(options.encode('utf-8'))>MAX_OPTS_BYTES:
        raise ProcessingError('Options payload is too large.')
    try:
        opts=json.loads(options)
        if not isinstance(opts,dict):raise ValueError('options should be an object')
    except (ValueError,TypeError): raise ProcessingError('Invalid tool options.')
    if not PROCESS_SLOTS.acquire(blocking=False):
        raise HTTPException(status_code=429,detail='Processor is busy. Please try again shortly.')
    wd=None
    try:
        wd=Path(tempfile.mkdtemp(prefix='doclyro_job_'))
        paths=await save_uploads(wd,files or [])
        result=await run_in_threadpool(process,slug,paths,opts,wd)
        if not result.is_file():raise ProcessingError('The converter did not generate a file.')
        background_tasks.add_task(shutil.rmtree,wd,ignore_errors=True)
        kind=mimetypes.guess_type(result.name)[0] or 'application/octet-stream'
        return FileResponse(str(result),filename=result.name,media_type=kind,
                            background=background_tasks)
    except ProcessingError:
        if wd is not None:shutil.rmtree(wd,ignore_errors=True)
        raise
    except Exception as e:
        logging.exception('Processing failure: %s',slug)
        if wd is not None:shutil.rmtree(wd,ignore_errors=True)
        raise ProcessingError('Unable to process this document. Check the input format and options.')
    finally:
        PROCESS_SLOTS.release()

@app.post('/api/inspect')
async def inspect(request:Request,file:UploadFile=File(...), password:str=Form('')):
    limit_request(request)
    wd=Path(tempfile.mkdtemp(prefix='pdfcraft_preview_'))
    try:
        fs=await save_uploads(wd,[file]);f=fs[0]
        with pdfopen(f,{'password':password}) as d:
            return {'pages':len(d),'size_bytes':f.stat().st_size,
                    'width':round(d[0].rect.width) if len(d) else 0,
                    'height':round(d[0].rect.height) if len(d) else 0,
                    'page_sizes':[{'width':round(p.rect.width,2),'height':round(p.rect.height,2),'rotation':p.rotation} for p in list(d)[:200]],
                    'form_fields':[{'name':w.field_name,'type':w.field_type_string,'value':w.field_value} for pg in list(d)[:50] for w in (pg.widgets() or [])][:100]}
    except ProcessingError:raise
    except Exception as e:raise ProcessingError('Could not inspect this PDF: '+str(e))
    finally:shutil.rmtree(wd,ignore_errors=True)

@app.post('/api/suggest-fields')
async def suggest_fields(request:Request,file:UploadFile=File(...),password:str=Form('')):
    limit_request(request)
    wd=Path(tempfile.mkdtemp(prefix='pdfcraft_suggest_'))
    try:
        fs=await save_uploads(wd,[file])
        with pdfopen(fs[0],{'password':password}) as d:
            return {'suggestions':detect_labeled_fields(d),
                    'note':'Heuristic suggestions; review placement before creating fields.'}
    finally:shutil.rmtree(wd,ignore_errors=True)

@app.post('/api/thumbnail')
async def thumbnail(request:Request,file:UploadFile=File(...), page:int=Form(1), password:str=Form('')):
    limit_request(request)
    if page < 1 or page > 500:raise ProcessingError('Invalid page number')
    wd=Path(tempfile.mkdtemp(prefix='pdfcraft_thumbnail_'))
    try:
        fs=await save_uploads(wd,[file]);f=fs[0]
        with pdfopen(f,{'password':password}) as d:
            if page<1 or page>len(d):raise ProcessingError('Page not found')
            p=d[page-1]
            if p.rect.width*p.rect.height*0.36>3_000_000:raise ProcessingError('Page is too large to preview.')
            pix=p.get_pixmap(matrix=__import__('fitz').Matrix(0.6,0.6),alpha=False)
            out=wd/'thumbnail.png';pix.save(str(out))
        # image bytes are tiny, avoid returning a path that background cleanup may invalidate
        from fastapi.responses import Response
        return Response(content=out.read_bytes(),media_type='image/png',
                        headers={'Cache-Control':'no-store'})
    finally:shutil.rmtree(wd,ignore_errors=True)

@app.post('/api/compare-preview')
async def compare_preview(request:Request,files:list[UploadFile]=File(...),page:int=Form(1),
                          width:int=Form(720),password:str=Form('')):
    limit_request(request)
    if len(files)!=2:
        raise ProcessingError('Upload two PDFs to preview differences.')
    if not 1<=page<=500 or not 320<=width<=1200:
        raise ProcessingError('Invalid comparison page or preview width.')
    wd=Path(tempfile.mkdtemp(prefix='pdfcraft_comparison_'))
    try:
        paths=await save_uploads(wd,files)
        if any(path.suffix.lower()!='.pdf' for path in paths):
            raise ProcessingError('Both comparison inputs must be PDF files.')
        from .compare_views import compare_page
        try:return compare_page(paths[0],paths[1],page,width,password)
        except ValueError as e:raise ProcessingError(str(e))
    finally:shutil.rmtree(wd,ignore_errors=True)


@app.post('/api/signature-inspect')
async def signature_inspect(request:Request,file:UploadFile=File(...)):
    limit_request(request)
    wd=Path(tempfile.mkdtemp(prefix='pdfcraft_siginspect_'))
    try:
        paths=await save_uploads(wd,[file])
        if paths[0].suffix.lower()!='.pdf':
            raise ProcessingError('Upload a PDF file.')
        from .digital_signing import inspect_signatures, SignatureError
        try:return {'signatures':inspect_signatures(paths[0]),
                    'warning':'Cryptographic integrity checked. Certificate trust and signer identity NOT evaluated.'}
        except SignatureError as e:raise ProcessingError(str(e))
    finally:shutil.rmtree(wd,ignore_errors=True)


from .workspace import router as workspace_router
# Free Render instances discard local SQLite and vault data on restart/sleep.
# Never expose registration, document vault or link-signing on ephemeral storage.
if not EPHEMERAL_MODE:
    app.include_router(workspace_router)
    from .cloud import router as cloud_router
    app.include_router(cloud_router)

app.mount('/',StaticFiles(directory=str(ROOT/'static'),html=True),name='static')
