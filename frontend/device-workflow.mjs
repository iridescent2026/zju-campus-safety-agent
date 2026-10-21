import {factoryRequest,factorySession,setFactorySession} from './factory-client.mjs';
import {factoryRefresh} from './factory-refresh.mjs';
import {initBusinessEvidence} from './business-evidence.mjs?v=28';
const roles={safety:'安全员',maintenance:'维修员',reviewer:'复核员',observer:'只读员',collector:'采集账号',admin:'管理员'};
export function initDeviceWorkflow(host){
 const panel=document.createElement('section');panel.id='device-workflow';panel.className='workflow-console';
 panel.innerHTML=`<div class="workflow-heading"><div><span class="eyebrow">CAMPUS INVESTIGATION / AI CHAT</span><h3>校园核查与通用 AI 助手</h3><p>自由提问先由模型识别：模板问题按后台依据回答，其余由模型回答 · 工单需人工确认</p></div><button id="workflow-refresh">更新核查依据</button></div>
 <div class="workflow-account"><strong>当前操作账号</strong> <span id="workflow-user">读取登录身份…</span><p>使用页首账号中心与切换账号；本页全部操作共用已登录身份。</p></div>
 <div class="analysis-controls"><label>核查设备<select id="workflow-entity"><option value="B-05">B-05 · 校园排水泵组</option></select></label><label class="workflow-test-rule"><input id="workflow-test-rule" type="checkbox"> 使用流程测试条件（60℃，非工程限值）</label><button id="workflow-highlight">查看关联对象</button></div>
 <p id="workflow-status" role="status">正在读取同源观测…</p><div id="workflow-facts" class="workflow-facts"></div><details><summary>最小台账与待核验依据</summary><div id="workflow-ledger"></div></details>
 <div class="workflow-questions analysis-controls"><button data-workflow-question="现在是什么状态？">1 状态</button><button data-workflow-question="可能影响哪里？">2 候选影响</button><button data-workflow-question="涉及哪些人员和作业？">3 人员与作业</button><button data-workflow-question="帮我安排核查任务。">4 核查草案</button><button data-workflow-question="处理后怎么关闭？">5 维修复核</button></div>
 <p id="workflow-language-status" class="account-note">语言理解：读取配置…</p><details id="workflow-conversation"><summary>本次对话记录</summary><div id="workflow-history"></div></details><button id="workflow-clear" type="button">清空对话</button><form id="workflow-ask" class="workflow-ask"><label>任务问题<input id="workflow-query" maxlength="2000" value="B-05 现在是什么状态？" aria-describedby="workflow-query-help" placeholder="输入编号或设备名称，如 b01、高压柜、plc柜" required></label><button>执行查询</button></form><p id="workflow-query-help" class="account-note">支持大小写编号、设备全名与常用简称。试试“b01什么状态”“高压柜正常吗”“plc柜运行情况”“B区空压机状态”；重名设备会列出候选供你确认。</p><p id="workflow-answer-source" class="account-note" role="status"></p><p id="workflow-answer" role="status">问答会执行后台工具，并显示实际结果；不会直接操作现场设备。</p>
 <details open><summary>核查依据与执行记录 · 工具调用记录（可追溯）</summary><div id="workflow-tools"></div></details>
 <div id="workflow-draft" class="workflow-draft" hidden><h4>待确认的核查草案</h4><p id="workflow-draft-text"></p><label>指派维修账号<select id="workflow-assignee"></select></label><button id="workflow-confirm">确认并创建核查工单</button><p>确认前重新核对观测有效性与台账。聊天生成草案不等于已派单；草案五分钟过期。</p></div>
 <p class="analysis-boundary">这是带证据的规则工具编排原型。连接、工程规则、实际组织岗位待现场核验；无规则返回待核验，缺失或过期返回未知。</p>`;
 host.querySelector('.module-heading').after(panel);
 const journey=document.createElement('section');journey.className='campus-journey';journey.setAttribute('aria-label','校园排水泵核查主线');
 journey.innerHTML=`<div><span class="eyebrow">CAMPUS SERVICE / SCENARIO</span><h4>后勤排水泵异常，如何协同核查？</h4><p>工程训练中心与后勤楼为示意场景。按后台观测核对状态、候选影响和区域人员，人工确认后进入维修复核。</p></div><nav aria-label="核查流程"><button type="button" data-campus-question="B05现在什么状态">01 查状态</button><button type="button" data-campus-question="B05坏了有什么影响">02 核影响</button><button type="button" data-campus-question="B05涉及哪些人员和作业">03 查人员作业</button><button type="button" data-campus-question="为B05安排核查任务">04 准备草案</button><button type="button" data-campus-orders>05 维修与复核</button></nav><p class="account-note">点击只执行所选步骤；草案需确认才派单，维修提交后由另一账号复核。</p>`;panel.querySelector('.workflow-heading').after(journey);
 initBusinessEvidence(panel);
 const $=id=>panel.querySelector('#'+id),node=(tag,value)=>{const n=document.createElement(tag);n.textContent=value;return n;};
 let current=null,draft=null,sequence=0,externalToken=null,history=[];
 const TOOL_LABELS={get_device_observation:'读取设备观测',query_relationships:'查询候选关联',query_area_personnel:'核对区域人员',query_work_plans:'检查作业计划',query_work_orders:'查询工单记录',interpret_question:'理解问题意图',general_chat:'模型回答',grounded_chat:'AI 依据回答',prepare_investigation_draft:'生成核查草案'};
 function toolSummary(t){
  const o=t.output||{};
  switch(t.tool){
   case 'get_device_observation':return [o.id&&o.title?o.id+' · '+o.title:'',o.statusLabel||''].filter(Boolean).join(' · ');
   case 'query_relationships':return Array.isArray(o.nodes)?'候选关联 '+o.nodes.length+' 项'+(o.hasUnverified?' · 含待核验连接':''):'';
   case 'query_area_personnel':return Array.isArray(o.valid)?'有效位置 '+o.valid.length+' 人 · 同区域未知 '+(Array.isArray(o.unknownInWorkArea)?o.unknownInWorkArea.length:0)+' 人':'';
   case 'query_work_plans':return Array.isArray(o.items)?'相关作业 '+o.items.length+' 项 · 时段范围重叠 '+(Array.isArray(o.conflicts)?o.conflicts.length:0)+' 组':'';
   case 'query_work_orders':return Array.isArray(o)?'该设备工单 '+o.length+' 张':'';
   case 'interpret_question':return Array.isArray(o.intents)?'意图：'+(o.intents.join(' / ')||'通用问答'):'';
   case 'grounded_chat':case 'general_chat':return '只读回答'+(o.model?' · '+o.model:'');
   case 'prepare_investigation_draft':return o.draftId?'草案 '+o.draftId+' · 尚未创建工单':'';
   default:return '';
  }
 }
 function renderTrace(list){
  const target=$('workflow-tools');if(!target)return;
  const steps=(list||[]).filter(Boolean);
  if(!steps.length){const empty=node('p','本次没有产生工具调用。');empty.className='ai-trace-empty';target.replaceChildren(empty);return;}
  const total=steps.reduce((sum,step)=>sum+(Number(step.elapsedMs)||0),0);
  const head=document.createElement('div');head.className='ai-trace-head';
  const title=document.createElement('strong');title.textContent='核查依据与执行记录';
  const count=document.createElement('span');count.textContent=steps.length+' 个工具步骤';
  const time=document.createElement('span');time.append(document.createTextNode('总耗时 '));const clock=document.createElement('b');clock.textContent=Math.round(total)+' ms';time.append(clock);
  head.append(title,count,time);
  const grid=document.createElement('div');grid.className='ai-trace';
  steps.forEach((step,index)=>{
   const state=step.status==='success'?'':step.status==='fallback'?' is-fallback':' is-fail';
   const row=document.createElement('div');row.className='ai-trace-step'+state;
   const no=document.createElement('span');no.className='ai-trace-no';no.textContent='0'+(index+1);
   const name=document.createElement('span');name.className='ai-trace-name';name.textContent=TOOL_LABELS[step.tool]||step.tool;
   const elapsed=document.createElement('span');elapsed.className='ai-trace-time';elapsed.textContent=step.elapsedMs==null?'':Math.round(step.elapsedMs)+' ms';
   const detail=document.createElement('p');detail.className='ai-trace-detail';
   const summary=toolSummary(step);
   const note=step.status==='success'?'已执行':step.status==='fallback'?'已回退本地规则':'未完成';
   detail.textContent=[summary,note+(step.status==='success'?'':' · '+((step.output&&step.output.reason)||step.status))].filter(Boolean).join('　|　');
   row.append(no,name,elapsed,detail);grid.append(row);
  });
  target.replaceChildren(head,grid);
 }

 function clearConversation(){sequence++;externalToken=null;history=[];renderDraft(null);$('workflow-answer-source').textContent='';$('workflow-history').replaceChildren();$('workflow-answer').textContent='对话已清空，可以提出新的问题。';}
 journey.querySelectorAll('[data-campus-question]').forEach(button=>button.addEventListener('click',()=>run(button,()=>{ $('workflow-query').value=button.dataset.campusQuestion;return ask(button.dataset.campusQuestion,'template');})));
 journey.querySelector('[data-campus-orders]').addEventListener('click',()=>window.dispatchEvent(new CustomEvent('campus-orders-open')));
 $('workflow-clear').addEventListener('click',clearConversation);
 function message(value,bad=false){$('workflow-status').textContent=value;$('workflow-status').classList.toggle('error',bad);}
 async function run(button,operation){if(button)button.disabled=true;try{await operation();}catch(e){message(e.message,true);}finally{if(button)button.disabled=false;}}
 function renderCase(value){current=value;const o=value.observation,names={temperature:'温度',pressure:'压力',voltage:'电压',current:'电流',leakage:'漏电',load:'负荷'},readings=Object.entries(o.measurements).map(([k,m])=>(names[k]||k)+' '+m.value+m.unit).join(' · ')||'无读数';
  const selector=$('workflow-entity');if([...selector.options].some(option=>option.value===o.id))selector.value=o.id;
  $('workflow-facts').replaceChildren(...[o.id+' · '+o.title+' · '+o.statusLabel,readings+(o.missingNote?' · '+o.missingNote:''),o.source+' · 采集 '+(o.observedAt?new Date(o.observedAt).toLocaleString():'未知'),`同源观测 v${value.factoryRevision} · 核查 ${new Date(value.capturedAt).toLocaleString()}`].map(v=>node('p',v)));
  $('workflow-ledger').replaceChildren(...value.ledger.map(r=>node('p',`${r.field}：${r.status} · ${r.basis}`)));
  renderTrace(value.toolResults);
  message(o.statusLabel+' · '+o.rule.basis);
 }
 async function refresh(){externalToken=null;const serial=++sequence,id=$('workflow-entity').value,value=await factoryRequest('/workflow/case/'+encodeURIComponent(id)+'?useTestRule='+$('workflow-test-rule').checked);if(serial===sequence)renderCase(value);}
 factoryRefresh.register('核查依据',{read:async()=>{if(!$('workflow-entity').value)throw new Error('设备台账尚在加载，请稍候重试');await refresh();}});
 function renderDraft(value){draft=value;$('workflow-confirm').disabled=!value||!!value?.case?.maintenanceCheck?.blocked;$('workflow-confirm').textContent=value?'确认 '+value.entityId+' 核查任务':'确认并创建核查工单';$('workflow-draft').hidden=!value;if(value)$('workflow-draft-text').textContent=`${value.id} · ${value.entityId} · ${value.reason} · 依据 v${value.case.factoryRevision} / ${value.case.observation.statusLabel} · 尚未创建工单`;}
 async function ask(query,answerMode='grounded'){externalToken=null;const serial=++sequence;renderDraft(null);$('workflow-answer-source').textContent='';$('workflow-answer').textContent=answerMode==='grounded'?'正在识别问题并选择模板或模型回答…':'正在查询本地模板…';let result;try{result=await factoryRequest('/workflow/chat',{query,entityId:$('workflow-entity').value,useTestRule:$('workflow-test-rule').checked,history,answerMode});}catch(e){if(serial===sequence)$('workflow-answer').textContent='本次查询未完成：'+e.message;throw e;}if(serial!==sequence)return;$('workflow-history').replaceChildren(...history.map(m=>node('p',(m.role==='user'?'你：':'助手：')+m.content)));$('workflow-answer').textContent=result.answer;const topic={status:'设备状态',impact:'故障影响',people:'人员与作业',responsibility:'责任记录',recommendations:'核查建议',review:'维修复核',general:'通用问答'}[result.intent]||'业务查询';$('workflow-answer-source').textContent=(result.engine?.endsWith('-classified-template')?'模型识别 · 本地模板':/grounded-chat|general-chat/.test(result.engine)?'AI 回答':result.engine==='rule-tool-fallback'?'AI 不可用，已回退本地核查':'本地模板')+' · '+topic;if(result.success)history=[...history,{role:'user',content:query.slice(0,4000)},{role:'assistant',content:result.answer.slice(0,3000)}].slice(-4);if(result.intent==='general'){renderTrace(result.tool_results||[]);}if(result.case)renderCase(result.case);if(result.draft)renderDraft(result.draft);}
 async function accounts(){const session=factorySession();$('workflow-user').textContent=session?.user?`${session.user.name} · ${roles[session.user.role]} · ${session.user.id}`:'未登录 · 可以查询，派单需登录';
  if(session){const users=await factoryRequest('/auth/users');$('workflow-assignee').replaceChildren(...users.filter(u=>u.role==='maintenance').map(u=>{const option=node('option',u.name+' · '+u.id);option.value=u.id;return option;}));}else $('workflow-assignee').replaceChildren();
 }
 $('workflow-refresh').addEventListener('click',e=>run(e.currentTarget,refresh));
 for(const id of ['workflow-entity','workflow-test-rule'])$(id).addEventListener('change',()=>{clearConversation();run(null,refresh);});
 $('workflow-ask').addEventListener('submit',e=>{e.preventDefault();run(e.submitter,()=>ask($('workflow-query').value));});
 panel.querySelectorAll('[data-workflow-question]').forEach(b=>b.addEventListener('click',()=>run(b,()=>ask($('workflow-entity').value+' '+b.dataset.workflowQuestion,'template'))));
 $('workflow-highlight').addEventListener('click',()=>{if(current)window.dispatchEvent(new CustomEvent('analysis-highlight',{detail:current.impact}));});
 $('workflow-confirm').addEventListener('click',e=>run(e.currentTarget,async()=>{if(!draft)throw new Error('请先生成核查草案');const confirmedDraft=draft,serial=sequence;renderDraft(null);const result=await factoryRequest('/workflow/drafts/'+confirmedDraft.id+'/confirm',{assignee:$('workflow-assignee').value});window.dispatchEvent(new CustomEvent('workflow-order-created',{detail:result.order}));if(serial!==sequence)return;$('workflow-answer').textContent=`${result.alreadyConfirmed?'此前已经创建':'已创建并指派'} ${result.order.id} → ${result.order.assignee}。尚未执行现场处理，请在维修闭环中继续。`;await refresh();}));
 window.addEventListener('factory-auth-change',()=>{clearConversation();run(null,accounts);});
 window.addEventListener('business-evidence-change',()=>{clearConversation();run(null,refresh);});
 window.addEventListener('workflow-request-start',e=>{sequence++;externalToken=e.detail.token;renderDraft(null);});
 window.addEventListener('workflow-chat-result',e=>{const result=e.detail;if(result.token&&result.token!==externalToken)return;sequence++;externalToken=null;renderDraft(null);$('workflow-answer-source').textContent='业务核查结果';$('workflow-answer').textContent=result.answer;if(result.case)renderCase(result.case);if(result.draft)renderDraft(result.draft);});
 window.addEventListener('factory-select',e=>{if(e.detail?.kind==='device'&&[...$('workflow-entity').options].some(o=>o.value===e.detail.id)){externalToken=null;$('workflow-entity').value=e.detail.id;renderDraft(null);run(null,refresh);}});
 run(null,async()=>{const [mode,data]=await Promise.all([factoryRequest('/auth/mode'),factoryRequest()]);$('workflow-test-rule').disabled=!mode.simulationEnabled;const language=$('workflow-language-status');if(language)language.textContent=mode.language?.configured?(mode.language.responsePolicy==='classified-template'?'自由提问：'+(mode.language.provider==='deepseek'?'DeepSeek':'模型')+' 识别意图，匹配模板后按后台依据回答；其他问题调用模型。快捷按钮直接使用模板。':'自由提问：AI 结合后台依据回答；快捷按钮：本地模板。设备状态与故障影响分别回答。'):'词典与上下文理解；支持多项查询和缺失条件追问，未配置大模型。';
  const entities=data.entities.filter(e=>e.kind==='device'&&(!document.body.classList.contains('factory-home')||e.view!=='overview'));$('workflow-entity').replaceChildren(...entities.map(e=>{const option=node('option',e.id+' · '+e.title);option.value=e.id;return option;}));$('workflow-entity').value='B-05';
  await accounts();await refresh();
 });
}
