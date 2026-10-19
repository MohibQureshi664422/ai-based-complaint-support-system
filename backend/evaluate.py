"""Independent small sample evaluation; results are not real-world validation."""
import csv,json,time,sys
from pathlib import Path
from sklearn.metrics import accuracy_score,classification_report,confusion_matrix
from support.ml import MODEL,PRIORITY_MODEL,SENTIMENT_MODEL,training_rows,signals,analyze,answer
ROOT=Path(__file__).parent

def read(path):
    with open(path,encoding='utf-8',newline='') as f:return list(csv.DictReader(f))
rows=read(sys.argv[1] if len(sys.argv)>1 else ROOT/'support/data/evaluation.csv')
if not rows:raise SystemExit('Empty evaluation dataset')
training={t.casefold().strip() for t,c in training_rows()}
if any(r['text'].casefold().strip() in training for r in rows):raise SystemExit('Exact training/test overlap detected')
start=time.perf_counter(); predictions=[MODEL.predict(r['text'])[0] for r in rows];elapsed=time.perf_counter()-start
truth=[r['category'] for r in rows]; labels=sorted(MODEL.documents)
result={'category':{'sample_count':len(rows),'accuracy':accuracy_score(truth,predictions),'report':classification_report(truth,predictions,labels=labels,output_dict=True,zero_division=0),'confusion_matrix':confusion_matrix(truth,predictions,labels=labels).tolist(),'labels':labels,'mean_inference_ms':elapsed*1000/len(rows)}}
test=read(ROOT/'support/data/signals_evaluation.csv')
if any(r['text'].casefold().strip() in {s['text'].casefold().strip() for s in signals} for r in test):raise SystemExit('Signal training/test overlap detected')
for name,model in [('priority',PRIORITY_MODEL),('sentiment',SENTIMENT_MODEL)]:
    actual=[r[name] for r in test]; predicted=model.predict([r['text'] for r in test]).tolist()
    result[name]={'sample_count':len(test),'accuracy':accuracy_score(actual,predicted),'report':classification_report(actual,predicted,output_dict=True,zero_division=0)}
start=time.perf_counter()
for r in rows: analyze(r['text']);answer(r['text'])
result['combined_model_and_faq_mean_ms']=(time.perf_counter()-start)*1000/len(rows)
result['limitations']='Tiny manually authored English examples; not a public benchmark or representative real-world accuracy. Priority metric evaluates learned model alone; safety keywords can override it in the app. No human satisfaction/usability results have been collected.'
(ROOT/'evaluation_report.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
