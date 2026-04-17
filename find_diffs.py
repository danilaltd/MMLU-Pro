import json
import os

USE_ELEN = True
USE_ORION = False
USE_PLAIN = True

folders = {}
if USE_ELEN:  folders["elen"] = "eval_results/elen_pro"
if USE_ORION: folders["orion"] = "eval_results/orion_pro"
if USE_PLAIN: folders["plain"] = "eval_results/plain_gemini"

subjects = ["business", "biology", "computer science", "engineering", "history", "law", "math", "psychology"]

def load_results(folder, subject):
    if not folder: return {}
    path = os.path.join(folder, f"{subject}_result.json")
    if not os.path.exists(path): return {}
    with open(path, 'r', encoding='utf-8') as f:
        return {item['question'].strip(): item for item in json.load(f)}

print(f"{'SUBJECT':<18} | {'STATUS':<25} | QUESTION SNIPPET")
print("-" * 110)

if os.path.exists("detailed_diffs.log"): os.remove("detailed_diffs.log")

for sub in subjects:
    res_elen = load_results(folders.get('elen'), sub) if USE_ELEN else {}
    res_orion = load_results(folders.get('orion'), sub) if USE_ORION else {}
    res_plain = load_results(folders.get('plain'), sub) if USE_PLAIN else {}

    active_results = [r for r in [res_elen, res_orion, res_plain] if r]
    if not active_results: continue
    
    all_questions = set().union(*[r.keys() for r in active_results])
    
    active_lens = [len(r) for r in [res_elen, res_orion, res_plain] if (res_elen if USE_ELEN else False) or (res_orion if USE_ORION else False) or (res_plain if USE_PLAIN else False)]
    if len(set(len(r) for r in active_results)) > 1:
        c = []
        if USE_ELEN: c.append(f"Elen={len(res_elen)}")
        if USE_ORION: c.append(f"Orion={len(res_orion)}")
        if USE_PLAIN: c.append(f"Plain={len(res_plain)}")
        print(f"DEBUG {sub}: {' | '.join(c)} | Total Unique={len(all_questions)}")

    for q in all_questions:
        e, o, p = res_elen.get(q), res_orion.get(q), res_plain.get(q)
        ans = (e or o or p)['answer']
        
        ep = e['pred'] if e else "N/A"
        op = o['pred'] if o else "N/A"
        pp = p['pred'] if p else "N/A"

        active_preds = [v for v in [ep, op, pp] if v != "N/A"]
        is_error = any(v != ans for v in active_preds)
        is_mismatch = len(set(active_preds)) > 1
        is_incomplete = "N/A" in [ep if USE_ELEN else "SKIP", op if USE_ORION else "SKIP", pp if USE_PLAIN else "SKIP"]

        if is_error or is_mismatch or is_incomplete:
            status = "MISMATCH"
            
            if is_incomplete:
                status = "INCOMPLETE DATA"
                continue
            elif all(v != ans for v in active_preds):
                if is_mismatch:
                    status = "TOTAL FAILURE (DIVERGENT)"
                else:
                    status = "TOTAL FAILURE (UNIFIED)"
                    continue
            elif USE_PLAIN and pp != ans and pp != "N/A":
                if USE_ELEN and ep == ans:
                    status = "ELEN WIN (vs Plain)"
                    continue
                elif USE_ORION and op == ans:
                    status = "ORION WIN (vs Plain)"
                    continue
            
            elif USE_PLAIN and pp == ans:
                if USE_ELEN and ep != ans and ep != "N/A":
                    status = "ELEN LOSS (vs Plain)"
                elif USE_ORION and op != ans and op != "N/A":
                    status = "ORION LOSS (vs Plain)"
            

            snippet = q[:60].replace('\n', ' ') + "..."
            print(f"{sub[:18]:<18} | {status:<25} | {snippet}")
            
            with open("detailed_diffs.log", "a", encoding='utf-8') as log:
                log.write(f"\n{'='*30} SUBJECT: {sub} | STATUS: {status} {'='*30}\n")
                log.write(f"QUESTION: {q}\n")
                log.write(f"EXPECTED: {ans}\n\n")
                
                for name, data, pred in [("ELEN", e, ep), ("ORION", o, op), ("PLAIN", p, pp)]:
                    if {"ELEN": USE_ELEN, "ORION": USE_ORION, "PLAIN": USE_PLAIN}[name]:
                        if data:
                            res_str = "CORRECT" if pred == ans else "WRONG"
                            log.write(f"[{name}] Prediction: {pred} ({res_str})\n")
                            # if pred != ans:
                            #     log.write(f"--- REASONING ---\n{data.get('model_outputs', 'No CoT found')}\n")
                        else:
                            log.write(f"[{name}] No data for this question (N/A)\n")
                log.write("\n" + "-"*100 + "\n")