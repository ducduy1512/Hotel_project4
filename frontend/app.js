const $ = (s, r=document) => r.querySelector(s);
const $$ = (s, r=document) => [...r.querySelectorAll(s)];
const state = {token:localStorage.getItem('hotel_token')||'', user:JSON.parse(localStorage.getItem('hotel_user')||'null'), page:'dashboard', rows:[], cache:{}, currentEdit:null};
const navItems = [
 ['dashboard','Tổng quan','⌂'],['customers','Khách hàng','♙'],['room-types','Loại phòng','▦'],['rooms','Phòng','▣'],['bookings','Booking','▤'],['peak-seasons','Mùa cao điểm','◷'],['services','Dịch vụ','✧'],['payments','Thanh toán','₫'],['invoices','Hóa đơn','▧'],['reports','Báo cáo doanh thu','▥']
];
const cfg = {
 customers:{title:'Quản lý khách hàng',endpoint:'/api/customers/',singular:'khách hàng',id:'id',columns:[['id','Mã'],['ho_ten','Họ tên'],['cccd','CCCD'],['sdt','Số điện thoại']],fields:[['ho_ten','Họ tên','text',true],['cccd','CCCD','text',true],['sdt','Số điện thoại','text',true]]},
 'room-types':{title:'Quản lý loại phòng',endpoint:'/api/room-types/',singular:'loại phòng',id:'id',columns:[['id','Mã'],['ten','Tên loại'],['gia_co_ban','Giá cơ bản'],['suc_chua','Sức chứa']],fields:[['ten','Tên loại phòng','text',true],['gia_co_ban','Giá cơ bản (VNĐ)','number',true],['suc_chua','Sức chứa','number',true]]},
 rooms:{title:'Quản lý phòng',endpoint:'/api/rooms/',singular:'phòng',id:'id',columns:[['id','Mã'],['so_phong','Số phòng'],['ten_loai_phong','Loại phòng'],['trang_thai','Trạng thái']],fields:[['so_phong','Số phòng','text',true],['loai_phong_id','Loại phòng','select:roomtypes',true],['trang_thai','Trạng thái','select:roomstatus',true]]},
 bookings:{title:'Quản lý Booking',endpoint:'/api/bookings/',singular:'booking',id:'id',columns:[['id','Booking'],['so_phong','Phòng'],['ho_ten','Khách hàng'],['ngay_nhan','Ngày nhận'],['ngay_tra','Ngày trả'],['trang_thai','Trạng thái'],['tien_phong_du_kien','Tiền phòng'],['tien_phu_phi_mua_cao_diem','Phụ phí']],fields:[['phong_id','Phòng','select:rooms',true],['khach_id','Khách hàng','select:customers',true],['ngay_nhan','Ngày nhận','date',true],['ngay_tra','Ngày trả','date',true]]},
 'peak-seasons':{title:'Quản lý mùa cao điểm',endpoint:'/api/peak-seasons/',singular:'mùa cao điểm',id:'id',columns:[['id','Mã'],['so_phong','Phòng'],['tu_ngay','Từ ngày'],['den_ngay','Đến ngày'],['he_so_gia','Phụ thu']],fields:[['phong_id','Phòng','select:rooms',true],['tu_ngay','Từ ngày','date',true],['den_ngay','Đến ngày','date',true],['he_so_gia','Tỷ lệ phụ thu','select:rates',true]]},
 services:{title:'Quản lý dịch vụ',endpoint:'/api/services/',singular:'dịch vụ',id:'id',columns:[['id','Mã'],['ten','Dịch vụ'],['loai_dichvu','Loại'],['nhom_dich_vu','Nhóm'],['don_gia','Đơn giá'],['don_vi_tinh','Đơn vị'],['so_luong','SL mặc định'],['dang_hoat_dong','Kinh doanh'],['pham_vi','Phạm vi'],['so_phong','Phòng']],fields:[['loai_dichvu','Loại dịch vụ','select:servicetypes',true],['nhom_dich_vu','Nhóm dịch vụ','select:servicegroups',true],['ten','Tên dịch vụ','text',true],['don_gia','Đơn giá (VNĐ)','number',true],['don_vi_tinh','Đơn vị tính','text',true],['so_luong','Số lượng mặc định','number',true],['dang_hoat_dong','Trạng thái danh mục','select:active',true],['phong_id','Phòng (chỉ dùng cho dịch vụ mặc định)','select:rooms',false],['booking_id','Booking (dịch vụ phát sinh)','number',false]]},
 payments:{title:'Quản lý thanh toán',endpoint:'/api/payments/',singular:'thanh toán',id:'id',columns:[['id','Pay'],['booking_id','Booking'],['ngay_thanh_toan','Ngày thanh toán'],['tien_phong_ap_dung','Tiền phòng'],['tien_dich_vu','Tiền dịch vụ'],['tien_phu_phi_mua_cao_diem','Phụ phí mùa cao điểm'],['so_tien','Tổng Pay'],['method','Phương thức'],['status','Trạng thái']],fields:[['ngay_thanh_toan','Ngày thanh toán','datetime-local',false],['method','Phương thức','select:methods',false],['status','Trạng thái','select:paystatus',true]]},
 invoices:{title:'Quản lý hóa đơn',endpoint:'/api/invoices/',singular:'hóa đơn',id:'id',columns:[['id','Invoice'],['pay_id','Pay'],['booking_id','Booking'],['ho_ten','Khách hàng'],['so_phong','Phòng'],['tien_phong','Tiền phòng'],['tien_dich_vu','Dịch vụ'],['tien_phu_phi_mua_cao_diem','Phụ phí'],['tong_tien','Tổng tiền'],['ngay_lap','Ngày lập']],fields:[]}
};
const opts={servicetypes:[['TUY_CHON','Dịch vụ bổ sung tính phí'],['MAC_DINH','Dịch vụ mặc định miễn phí']],servicegroups:[['AN_SANG','Ăn sáng'],['GIUONG_PHU','Giường phụ'],['GIAT_UI','Giặt ủi'],['MINIBAR','Minibar'],['DUA_DON','Đưa đón'],['TRANG_TRI','Trang trí'],['DO_DUNG','Đồ dùng phòng'],['KHAC','Khác']],active:[['1','Đang kinh doanh'],['0','Ngừng cung cấp']],roomstatus:[['SAN_SANG','Sẵn sàng'],['BAO_TRI','Bảo trì']],rates:[['0.10','10%'],['0.20','20%'],['0.25','25%'],['0.30','30%'],['0.35','35%'],['0.40','40%'],['0.50','50%'],['0.60','60%']],methods:[['TIEN_MAT','Tiền mặt'],['CHUYEN_KHOAN','Chuyển khoản'],['THE','Thẻ']],paystatus:[['CHO_THANH_TOAN','Chờ thanh toán'],['THANH_CONG','Thành công'],['THAT_BAI','Thất bại'],['HOAN_TIEN','Hoàn tiền']]};
async function api(path, options={}){const headers={'Content-Type':'application/json',...(options.headers||{})};if(state.token)headers.Authorization=`Bearer ${state.token}`;const method=String(options.method||'GET').toUpperCase();const res=await fetch(path,{...options,headers,cache:method==='GET'?'no-store':options.cache});const type=res.headers.get('content-type')||'';let body=type.includes('json')?await res.json():await res.text();if(!res.ok){const msg=body?.detail||body?.message||`Lỗi HTTP ${res.status}`;throw new Error(typeof msg==='string'?msg:JSON.stringify(msg));}return body;}
function toast(msg,type='success'){const el=document.createElement('div');el.className=`toast ${type}`;el.textContent=msg;$('#toast-root').append(el);setTimeout(()=>el.remove(),4300)}
function money(v){if(v===null||v===undefined||v==='')return '—';return new Intl.NumberFormat('vi-VN',{style:'currency',currency:'VND',maximumFractionDigits:0}).format(Number(v));}
function dateText(v){if(!v)return '—';return String(v).replace('T',' ').replace('Z','').slice(0,16)}
function esc(v){return String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function badge(v){const s=String(v??'');let c='';if(['THANH_CONG','DA_XAC_NHAN','HOAN_THANH','SAN_SANG'].includes(s))c='green';else if(['CHO_THANH_TOAN','CHO_XAC_NHAN','DANG_O'].includes(s))c='orange';else if(['DA_HUY','THAT_BAI','BAO_TRI'].includes(s))c='red';else c='blue';return `<span class="badge ${c}">${esc(s.replaceAll('_',' '))}</span>`;}
function authScreen(mode='login'){const reg=mode==='register';$('#app').innerHTML=`<div class="auth-wrap"><section class="auth-visual"><div class="brand"><span class="brand-mark">⌂</span><div>HOTEL<br><small>MANAGEMENT SYSTEM</small></div></div><div class="hero-copy"><div class="eyebrow">Hospitality, thoughtfully managed</div><h1>Không gian nghỉ dưỡng, trải nghiệm trọn vẹn.</h1><p>Nền tảng quản lý khách sạn tích hợp đặt phòng, dịch vụ, thanh toán và báo cáo trên một hệ thống thống nhất.</p></div><div class="hero-foot">HOTEL MANAGEMENT SYSTEM · Database Project</div></section><section class="auth-panel"><form id="auth-form" class="auth-card"><div class="eyebrow">WELCOME ${reg?'NEW MEMBER':'BACK'}</div><h2>${reg?'Tạo tài khoản':'Đăng nhập'}</h2><p class="sub">${reg?'Đăng ký tài khoản khách hàng để đặt phòng trực tuyến.':'Đăng nhập để tiếp tục sử dụng hệ thống.'}</p>${reg?`<div class="field"><label>Họ và tên</label><input name="full_name" required minlength="2"></div><div class="field"><label>CCCD</label><input name="cccd" required minlength="9"></div><div class="field"><label>Số điện thoại</label><input name="sdt" required minlength="9"></div>`:''}<div class="field"><label>Tên đăng nhập</label><input name="username" autocomplete="username" required minlength="${reg?3:1}"></div><div class="field"><label>Mật khẩu</label><input name="password" type="password" autocomplete="${reg?'new-password':'current-password'}" required minlength="${reg?6:1}"></div><button class="btn btn-primary" type="submit">${reg?'Đăng ký tài khoản':'Đăng nhập'} <span>→</span></button><div class="auth-switch">${reg?'Đã có tài khoản?':'Chưa có tài khoản?'} <button class="link-btn" type="button" id="auth-switch">${reg?'Đăng nhập':'Đăng ký khách hàng'}</button></div></form></section></div>`;$('#auth-switch').onclick=()=>authScreen(reg?'login':'register');$('#auth-form').onsubmit=async e=>{e.preventDefault();const d=Object.fromEntries(new FormData(e.currentTarget));try{const r=await api(reg?'/api/auth/register':'/api/auth/login',{method:'POST',body:JSON.stringify(d)});if(reg){toast('Đăng ký thành công. Hãy đăng nhập.');authScreen('login');return;}state.token=r.access_token;state.user=r.user;localStorage.setItem('hotel_token',state.token);localStorage.setItem('hotel_user',JSON.stringify(state.user));renderShell();}catch(err){toast(err.message,'error');}};}
function renderShell(){if(!state.token||!state.user){authScreen();return;}const admin=state.user.role==='ADMIN';if(!admin&&!['customer-home','my-bookings','my-invoices'].includes(state.page))state.page='customer-home';if(admin&&['customer-home','my-bookings','my-invoices'].includes(state.page))state.page='dashboard';const menus=admin?navItems:[['customer-home','Đặt phòng','⌂'],['my-bookings','Booking của tôi','▤'],['my-invoices','Hóa đơn của tôi','▧']];$('#app').innerHTML=`<div class="layout"><aside class="sidebar" id="sidebar"><div class="side-brand"><span class="brand-mark">⌂</span><div><strong>HOTEL</strong><small>MANAGEMENT SYSTEM</small></div></div><div class="nav-label">MENU CHỨC NĂNG</div><nav class="nav">${menus.map(([k,t,i])=>`<button data-page="${k}" class="${state.page===k?'active':''}"><span class="nav-icon">${i}</span>${t}</button>`).join('')}</nav><div class="side-bottom">HOTEL MANAGEMENT<br>Database Management Project<br><span style="color:#587b99">REST API · HTML5 Interface</span></div></aside><section class="main"><header class="topbar"><div style="display:flex;align-items:center;gap:12px"><button class="btn btn-secondary menu-toggle" id="menu-toggle">☰</button><div class="top-title">${admin?'Hotel Management':'Customer Portal'}</div></div><div class="top-right"><div class="user-chip"><div class="avatar">${esc((state.user.full_name||'U')[0].toUpperCase())}</div><span class="name">${esc(state.user.full_name||state.user.username)}</span><span class="badge blue">${admin?'ADMIN':'CUSTOMER'}</span></div><button class="btn btn-outline btn-sm" id="logout">Đăng xuất</button></div></header><div class="content" id="content"><div class="loading-line">Đang tải dữ liệu…</div></div></section></div>`;$$('[data-page]').forEach(b=>b.onclick=()=>go(b.dataset.page));$('#logout').onclick=logout;$('#menu-toggle')?.addEventListener('click',()=>$('#sidebar').classList.toggle('open'));go(state.page||(admin?'dashboard':'customer-home'));}
function logout(){state.token='';state.user=null;localStorage.removeItem('hotel_token');localStorage.removeItem('hotel_user');state.page='dashboard';authScreen();}
function go(p){state.page=p;$$('[data-page]').forEach(b=>b.classList.toggle('active',b.dataset.page===p));$('#sidebar')?.classList.remove('open');if(p==='dashboard')dashboard();else if(cfg[p])listPage(p);else if(p==='reports')reportsPage();else if(p==='customer-home')customerHome();else if(p==='my-bookings')myBookings();else if(p==='my-invoices')myInvoices();}
async function dashboard(){const c=$('#content');c.innerHTML=`<div class="page-heading"><div><div class="eyebrow">OVERVIEW</div><h1>Tổng quan hoạt động</h1><p>Cập nhật dữ liệu vận hành khách sạn theo thời gian thực.</p></div></div><div class="stats-grid">${[1,2,3,4].map(()=>'<div class="stat-card"><div class="loading-line">…</div></div>').join('')}</div><div class="grid two-col"><div class="panel"><h3 class="panel-title">Booking gần đây</h3><div id="recent-bookings" class="loading-line">Đang tải…</div></div><div class="panel"><h3 class="panel-title">Tình trạng phòng</h3><div id="room-state" class="loading-line">Đang tải…</div></div></div>`;try{const [b,r,k,p,i]=await Promise.all([api('/api/bookings/'),api('/api/rooms/'),api('/api/customers/'),api('/api/payments/'),api('/api/invoices/')]);const payments=p.payments||[];const totalRevenue=payments.filter(x=>x.status==='THANH_CONG').reduce((s,x)=>s+Number(x.so_tien||0),0);$('.stats-grid').innerHTML=[['Tổng phòng',r.length,'▣','Đang quản lý'],['Booking',b.length,'▤','Tất cả trạng thái'],['Khách hàng',k.length,'♙','Hồ sơ khách'],['Doanh thu đã thu',money(totalRevenue),'₫','Giao dịch thành công']].map(([l,v,ic,n])=>`<div class="stat-card"><div class="stat-top"><span class="stat-label">${l}</span><span class="stat-icon">${ic}</span></div><div class="stat-value">${v}</div><div class="stat-note">${n}</div></div>`).join('');$('#recent-bookings').innerHTML=miniTable(b.slice(0,6),[['id','Booking'],['so_phong','Phòng'],['ho_ten','Khách'],['trang_thai','Trạng thái']]);const counts={SAN_SANG:0,DANG_SU_DUNG:0,BAO_TRI:0};r.forEach(x=>counts[x.trang_thai]=(counts[x.trang_thai]||0)+1);$('#room-state').innerHTML=Object.entries(counts).map(([k,v])=>`<div style="display:flex;justify-content:space-between;padding:13px 2px;border-bottom:1px solid var(--line)">${badge(k)}<b>${v} phòng</b></div>`).join('')+`<p class="muted" style="font-size:12px">${i.invoices?.length||0} hóa đơn đã phát hành</p>`;}catch(e){c.insertAdjacentHTML('beforeend',`<p class="badge red">${esc(e.message)}</p>`);}}
function miniTable(rows,cols){if(!rows.length)return '<div class="empty">Chưa có dữ liệu</div>';return `<div class="table-scroll"><table><thead><tr>${cols.map(c=>`<th>${c[1]}</th>`).join('')}</tr></thead><tbody>${rows.map(r=>`<tr>${cols.map(([k])=>`<td>${k==='trang_thai'||k==='status'?badge(r[k]):esc(r[k])}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;}
function valFmt(key,v){if(key.includes('tien')||key==='don_gia'||key==='gia_co_ban'||key==='so_tien')return money(v);if(key.includes('ngay'))return dateText(v);if(key==='trang_thai'||key==='status')return badge(v);if(key==='he_so_gia')return `${Math.round(Number(v)*100)}%`;if(key==='loai_dichvu')return v==='MAC_DINH'?'Mặc định miễn phí':v==='TUY_CHON'?'Bổ sung tính phí':esc(v);if(key==='pham_vi')return v==='DANH_MUC_CHUNG'?'Danh mục dùng chung':v==='PHONG'?'Theo phòng':esc(v);if(key==='nhom_dich_vu'){const m={AN_SANG:'Ăn sáng',GIUONG_PHU:'Giường phụ',GIAT_UI:'Giặt ủi',MINIBAR:'Minibar',DUA_DON:'Đưa đón sân bay',TRANG_TRI:'Trang trí',DO_DUNG:'Đồ dùng phòng',KHAC:'Khác'};return esc(m[v]||v);}if(key==='dang_hoat_dong')return Number(v)?'<span class="badge green">Đang kinh doanh</span>':'<span class="badge red">Ngừng cung cấp</span>';return esc(v);}
async function listPage(key){const conf=cfg[key],c=$('#content');c.innerHTML=`<div class="page-heading"><div><div class="eyebrow">MANAGEMENT</div><h1>${conf.title}</h1><p>${key==='peak-seasons'?'Thiết lập khoảng ngày cao điểm cho tất cả phòng; mỗi phòng giữ mức phụ thu riêng và khách sẽ thấy giá trước khi đặt.':'Theo dõi, tìm kiếm và quản lý dữ liệu trên hệ thống.'}</p></div><div class="heading-actions">${key==='invoices'?'<button class="btn btn-primary" id="new-invoice">＋ Lập hóa đơn</button>':key==='payments'?'<button class="btn btn-secondary" id="webhooks">Nhật ký QR</button><button class="btn btn-primary" id="new-invoice">＋ Tạo Pay / hóa đơn</button>':key==='services'?'<button class="btn btn-primary" id="new-service">＋ Thêm dịch vụ</button>':key==='peak-seasons'?'<button class="btn btn-primary" id="create">＋ Tạo mùa cho tất cả phòng</button>':`<button class="btn btn-primary" id="create">＋ Thêm ${conf.singular}</button>`}</div></div><div class="table-panel"><div class="toolbar" style="padding:15px 16px 0"><div class="search-wrap"><input class="search-input" id="search" placeholder="Tìm trong danh sách…"></div><button class="btn btn-outline btn-sm" id="refresh">↻ Làm mới</button></div><div id="table-area" class="loading-line">Đang tải danh sách…</div><div class="table-foot" id="table-count"></div></div>`;$('#refresh').onclick=()=>listPage(key);$('#search').oninput=()=>renderTable(key);if(key==='invoices')$('#new-invoice').onclick=()=>invoiceCreate();else if(key==='payments'){$('#webhooks').onclick=webhookList;$('#new-invoice').onclick=()=>invoiceCreate();}else if(key==='services')$('#new-service').onclick=()=>openForm(key);else if(key==='peak-seasons')$('#create').onclick=()=>openPeakSeasonBulkForm();else $('#create').onclick=()=>openForm(key);try{let data=await api(conf.endpoint);if(key==='payments')data=data.payments||[];if(key==='invoices')data=data.invoices||[];state.cache[key]=data;state.rows=data;renderTable(key);}catch(e){$('#table-area').innerHTML=`<div class="empty">Không tải được dữ liệu: ${esc(e.message)}</div>`;}}
function renderTable(key){const conf=cfg[key],area=$('#table-area');if(!area)return;const q=($('#search')?.value||'').toLowerCase();const rows=(state.cache[key]||[]).filter(r=>!q||Object.values(r).some(v=>String(v??'').toLowerCase().includes(q)));if(!rows.length){area.innerHTML='<div class="empty">Không có dữ liệu phù hợp.</div>';$('#table-count').textContent='0 bản ghi';return;}const columns=conf.columns;area.innerHTML=`<div class="table-scroll"><table><thead><tr>${columns.map(x=>`<th>${x[1]}</th>`).join('')}<th>Thao tác</th></tr></thead><tbody>${rows.map(r=>`<tr>${columns.map(([k])=>`<td>${valFmt(k,r[k])}</td>`).join('')}<td><div class="actions">${key==='bookings'?bookingActions(r):key==='payments'?paymentActions(r):key==='invoices'?'<button class="btn btn-outline btn-sm" data-view="'+r.id+'">Chi tiết</button>':key==='room-types'?`<button class="btn btn-success btn-sm" data-room-type-services="${r.id}">Dịch vụ mặc định</button><button class="btn btn-outline btn-sm" data-edit="${r[conf.id]}">Sửa</button><button class="btn btn-danger btn-sm" data-delete="${r[conf.id]}">Xóa</button>`:`<button class="btn btn-outline btn-sm" data-edit="${r[conf.id]}">Sửa</button><button class="btn btn-danger btn-sm" data-delete="${r[conf.id]}">Xóa</button>`}</div></td></tr>`).join('')}</tbody></table></div>`;$('#table-count').textContent=`Hiển thị ${rows.length} / ${(state.cache[key]||[]).length} bản ghi`;$$('[data-edit]',area).forEach(b=>b.onclick=()=>openForm(key,rows.find(x=>String(x[conf.id])===b.dataset.edit)));$$('[data-delete]',area).forEach(b=>b.onclick=()=>removeRecord(key,b.dataset.delete));$$('[data-action]',area).forEach(b=>b.onclick=()=>bookingAction(b.dataset.action,b.dataset.id));$$('[data-status]',area).forEach(b=>b.onclick=()=>editPaymentStatus(rows.find(x=>String(x.id)===b.dataset.id)));$$('[data-view]',area).forEach(b=>b.onclick=()=>viewInvoice(b.dataset.view));$$('[data-booking-view]',area).forEach(b=>b.onclick=()=>viewBooking(b.dataset.bookingView));$$('[data-booking-edit]',area).forEach(b=>b.onclick=()=>openForm('bookings',rows.find(x=>String(x.id)===b.dataset.bookingEdit)));$$('[data-payment-delete]',area).forEach(b=>b.onclick=()=>deletePayment(b.dataset.paymentDelete));$$('[data-room-type-services]',area).forEach(b=>b.onclick=()=>openRoomTypeServices(b.dataset.roomTypeServices));}
function bookingActions(r){let a=[`<button class="btn btn-outline btn-sm" data-booking-view="${r.id}">Chi tiết</button>`];if(['CHO_XAC_NHAN','DA_XAC_NHAN'].includes(r.trang_thai))a.push(`<button class="btn btn-outline btn-sm" data-booking-edit="${r.id}">Sửa</button>`);if(r.trang_thai==='CHO_XAC_NHAN')a.push(`<button class="btn btn-success btn-sm" data-action="confirm" data-id="${r.id}">Xác nhận</button>`);if(r.trang_thai==='DA_XAC_NHAN')a.push(`<button class="btn btn-outline btn-sm" data-action="check-in" data-id="${r.id}">Nhận phòng</button>`);if(r.trang_thai==='DANG_O')a.push(`<button class="btn btn-outline btn-sm" data-action="check-out" data-id="${r.id}">Trả phòng</button>`);if(!['DA_HUY','HOAN_THANH'].includes(r.trang_thai))a.push(`<button class="btn btn-danger btn-sm" data-action="cancel" data-id="${r.id}">Hủy</button>`);return a.join('');}
function paymentActions(r){return `<button class="btn btn-outline btn-sm" data-status="1" data-id="${r.id}">Sửa</button><button class="btn btn-danger btn-sm" data-payment-delete="${r.id}">Xóa</button>`;}
async function bookingAction(action,id){const names={confirm:'confirm', 'check-in':'check-in','check-out':'check-out',cancel:null};if(action==='cancel'&&!confirm('Bạn chắc chắn muốn hủy Booking này?'))return;try{await api(`/api/bookings/${id}/${action==='cancel'?'':names[action]}`.replace(/\/$/,''),{method:action==='cancel'?'DELETE':'POST',body:action==='cancel'?undefined:'{}'});toast('Đã cập nhật Booking.');listPage('bookings');}catch(e){toast(e.message,'error');}}
async function editPaymentStatus(r){const d=(r.ngay_thanh_toan||'').toString().replace(' ','T').slice(0,16);openModal(`Cập nhật Pay #${r.id}`,`<form id="entity-form"><div class="form-grid"><div class="field"><label>Ngày thanh toán</label><input type="datetime-local" name="ngay_thanh_toan" value="${esc(d)}"></div><div class="field"><label>Phương thức</label><select name="method">${opts.methods.map(([v,l])=>`<option value="${v}" ${v===r.method?'selected':''}>${l}</option>`).join('')}</select></div><div class="field full"><label>Trạng thái</label><select name="status">${opts.paystatus.map(([v,l])=>`<option value="${v}" ${v===r.status?'selected':''}>${l}</option>`).join('')}</select><small>Số tiền hiện tại: ${money(r.so_tien)}. Tổng tiền được kiểm tra bởi API/Database.</small></div></div><div class="form-actions"><button class="btn btn-secondary" type="button" data-close>Đóng</button><button class="btn btn-primary">Lưu thay đổi</button></div></form>`);$('#entity-form').onsubmit=async e=>{e.preventDefault();const f=Object.fromEntries(new FormData(e.currentTarget));const payload={status:f.status,method:f.method};if(f.ngay_thanh_toan)payload.ngay_thanh_toan=f.ngay_thanh_toan.replace('T',' ')+':00';try{await api(`/api/payments/${r.id}`,{method:'PUT',body:JSON.stringify(payload)});closeModal();toast('Đã cập nhật thanh toán.');listPage('payments');}catch(x){toast(x.message,'error');}};}
async function deletePayment(id){if(!confirm(`Xóa giao dịch Pay #${id}? Database sẽ từ chối nếu giao dịch đã gắn hóa đơn/thanh toán hoàn tất.`))return;try{await api(`/api/payments/${id}`,{method:'DELETE'});toast('Đã xóa giao dịch.');listPage('payments');}catch(e){toast(e.message,'error');}}
async function viewBooking(id){try{const r=await api(`/api/bookings/${id}`);const detail=r.dich_vu||[];openModal(`Chi tiết Booking #${id}`,`<div class="invoice-summary">${[['Phòng',r.so_phong],['Khách hàng',r.ho_ten],['Nhận phòng',dateText(r.ngay_nhan)],['Trả phòng',dateText(r.ngay_tra)],['Trạng thái',r.trang_thai],['Tiền phòng',money(r.tien_phong_du_kien)],['Phụ phí mùa cao điểm',money(r.tien_phu_phi_mua_cao_diem)]].map(([k,v])=>`<div class="summary-row"><span>${k}</span><b>${esc(v)}</b></div>`).join('')}</div><h4 style="font:700 13px Manrope;margin:18px 0 8px">Dịch vụ đã chọn</h4>${miniTable(detail,[['dichvu_id','Mã'],['ten','Dịch vụ'],['don_gia','Đơn giá'],['so_luong','Số lượng'],['thanh_tien','Thành tiền']])}`);}catch(e){toast(e.message,'error');}}

async function loadSelect(type){if(type==='rooms')return (await api('/api/rooms/')).map(x=>[x.id,`Phòng ${x.so_phong} · ${x.ten_loai_phong}`]);if(type==='roomtypes')return (await api('/api/room-types/')).map(x=>[x.id,x.ten]);if(type==='customers')return (await api('/api/customers/')).map(x=>[x.id,`${x.ho_ten} (#${x.id})`]);if(opts[type])return opts[type];return [];}
async function formMarkup(key,row={}){const conf=cfg[key];let html='';const defaults={loai_dichvu:'TUY_CHON',nhom_dich_vu:'KHAC',don_vi_tinh:'lần',so_luong:1,dang_hoat_dong:1};for(const [name,label,type,required] of conf.fields){let value=row[name]??defaults[name]??'';let input='';if(type.startsWith('select:')){const options=await loadSelect(type.split(':')[1]);input=`<select name="${name}" ${required?'required':''}><option value="">-- Chọn --</option>${options.map(([v,l])=>`<option value="${v}" ${String(v)===String(value)?'selected':''}>${esc(l)}</option>`).join('')}</select>`;}else input=`<input name="${name}" type="${type}" value="${esc(value)}" ${required?'required':''} ${type==='number'?'step="any" min="0"':''}>`;html+=`<div class="field"><label>${label}</label>${input}</div>`;}if(key==='services')html=`<p class="muted full service-config-note">Danh mục tính phí: chọn “Dịch vụ bổ sung”, để trống Phòng và Booking, nhập giá lớn hơn 0. Dịch vụ mặc định phải gắn với Phòng và có giá 0. Dịch vụ bổ sung chỉ xuất hiện cho khách khi đang kinh doanh.</p>${html}`;return `<form id="entity-form"><div class="form-grid">${html}</div><div class="form-actions"><button type="button" class="btn btn-secondary" data-close>Hủy</button><button class="btn btn-primary">${row.id?'Lưu thay đổi':'Tạo mới'}</button></div></form>`;}
async function openForm(key,row=null){const conf=cfg[key];const body=await formMarkup(key,row||{});openModal(`${row?'Cập nhật':'Thêm'} ${conf.singular}`,body);$('#entity-form').onsubmit=async e=>{e.preventDefault();const form=new FormData(e.currentTarget),payload={};for(const [name,,type] of conf.fields){let v=form.get(name);if(type==='number'||type.startsWith('select:')&&v!==''&&(name==='phong_id'||name==='loai_phong_id'||name==='booking_id'||name==='dang_hoat_dong'))v=v===''?null:Number(v);payload[name]=v===''?null:v;}if(key==='services'){payload.booking_id=payload.booking_id||null;payload.phong_id=payload.phong_id||null;if(payload.booking_id!==null){if((payload.loai_dichvu==='TUY_CHON'&&Number(payload.don_gia)<=0)||(payload.loai_dichvu==='MAC_DINH'&&Number(payload.don_gia)!==0)){toast('Giá dịch vụ Booking không khớp loại dịch vụ.','error');return;}}else if(payload.loai_dichvu==='TUY_CHON'&&payload.phong_id===null){if(Number(payload.don_gia)<=0){toast('Dịch vụ bổ sung phải có đơn giá lớn hơn 0.','error');return;}}else if(payload.loai_dichvu==='MAC_DINH'){if(payload.phong_id===null||Number(payload.don_gia)!==0){toast('Dịch vụ mặc định phải gắn với phòng và có giá 0.','error');return;}}else if(payload.phong_id!==null){toast('Dịch vụ bổ sung toàn cục không được gắn với phòng.','error');return;}}try{await api(row?`${conf.endpoint}${row.id}`:conf.endpoint,{method:row?'PUT':'POST',body:JSON.stringify(payload)});closeModal();toast(`${row?'Cập nhật':'Thêm'} ${conf.singular} thành công.`);listPage(key);}catch(err){toast(err.message,'error');}};}
async function openModal(title,body){$('#modal-root').innerHTML=`<div class="modal-backdrop"><section class="modal"><div class="modal-head"><h3>${title}</h3><button class="icon-btn" data-close>×</button></div><div class="modal-body">${body}</div></section></div>`;$$('[data-close]').forEach(b=>b.onclick=closeModal);$('.modal-backdrop').onclick=e=>{if(e.target.classList.contains('modal-backdrop'))closeModal();};}
function closeModal(){$('#modal-root').innerHTML='';}
function roomTypeDefaultServiceRow(service={}){
 const qty=service.so_luong??service.so_luong_min??1;
 return `<div class="default-service-row" data-default-service-row>
  <div class="field"><label>Tên dịch vụ</label><input type="text" data-service-name maxlength="100" value="${esc(service.ten||'')}" placeholder="Ví dụ: Nước suối miễn phí"></div>
  <div class="field"><label>Đơn giá (VNĐ)</label><input type="number" data-service-price min="0" step="0.01" value="${esc(service.don_gia??0)}"></div>
  <div class="field"><label>Số lượng / phòng</label><input type="number" data-service-quantity min="1" step="1" value="${esc(qty)}"></div>
  <div class="default-service-remove"><button type="button" class="btn btn-danger btn-sm" data-remove-room-service> Xóa </button></div>
 </div>`;
}

async function openRoomTypeServices(roomTypeId){
 try{
  const data=await api(`/api/room-types/${roomTypeId}/default-services`);
  const roomType=data.room_type||{};
  const services=Array.isArray(data.services)?data.services:[];
  const initialRows=services.length?services:[{ten:'',don_gia:0,so_luong:1}];
  const warning=data.is_consistent===false?'<div class="service-config-warning">Một số phòng hiện có danh sách dịch vụ hoặc số lượng khác nhau. Khi lưu, hệ thống sẽ đồng bộ lại cùng một cấu hình cho tất cả phòng thuộc loại này.</div>':'';
  const noRooms=Number(data.room_count||0)===0;
  const roomNote=noRooms
   ?'<div class="service-config-warning">Loại phòng chưa có phòng thực tế. Hãy thêm ít nhất một phòng trước khi cấu hình dịch vụ mặc định.</div>'
   :`<p class="muted service-config-note">Cấu hình này sẽ được áp dụng cho toàn bộ <b>${Number(data.room_count)}</b> phòng thuộc loại <b>${esc(roomType.ten||'')}</b>. Khi khách đặt phòng, các dịch vụ được sao chép vào Booking; những Booking đã tạo trước đó vẫn giữ nguyên dữ liệu dịch vụ lịch sử.</p>`;
  openModal(`Dịch vụ mặc định · ${esc(roomType.ten||'Loại phòng')}`,`
   ${roomNote}${warning}
   <form id="room-type-default-services-form">
    <div class="default-service-list" id="room-type-default-service-list">${initialRows.map(roomTypeDefaultServiceRow).join('')}</div>
    <button type="button" class="btn btn-outline" id="add-room-type-default-service" ${noRooms?'disabled':''}>＋ Thêm dịch vụ</button>
    <div class="form-actions">
     <button type="button" class="btn btn-secondary" data-close>Hủy</button>
     <button type="submit" class="btn btn-primary" ${noRooms?'disabled':''}>Lưu và đồng bộ</button>
    </div>
   </form>`);
  const list=$('#room-type-default-service-list');
  $('#add-room-type-default-service').onclick=()=>list.insertAdjacentHTML('beforeend',roomTypeDefaultServiceRow());
  list.addEventListener('click',event=>{
   const remove=event.target.closest('[data-remove-room-service]');
   if(remove)remove.closest('[data-default-service-row]')?.remove();
  });
  $('#room-type-default-services-form').onsubmit=async event=>{
   event.preventDefault();
   const rows=[...list.querySelectorAll('[data-default-service-row]')];
   const payloadServices=[];
   for(const row of rows){
    const ten=row.querySelector('[data-service-name]').value.trim();
    const priceText=row.querySelector('[data-service-price]').value;
    const qtyText=row.querySelector('[data-service-quantity]').value;
    if(!ten||priceText===''||qtyText===''){toast('Vui lòng nhập đầy đủ tên, đơn giá và số lượng cho từng dịch vụ.','error');return;}
    const don_gia=Number(priceText),so_luong=Number(qtyText);
    if(!Number.isFinite(don_gia)||don_gia<0||!/^[0-9]+(?:\.[0-9]{1,2})?$/.test(priceText)){toast('Đơn giá phải là số không âm và tối đa 2 chữ số thập phân.','error');return;}
    if(!Number.isInteger(so_luong)||so_luong<=0){toast('Số lượng mỗi phòng phải là số nguyên lớn hơn 0.','error');return;}
    payloadServices.push({ten,don_gia,so_luong});
   }
   try{
    const result=await api(`/api/room-types/${roomTypeId}/default-services`,{method:'PUT',body:JSON.stringify({services:payloadServices})});
    closeModal();
    toast(result.message||'Đã đồng bộ dịch vụ mặc định.');
    listPage('room-types');
   }catch(error){toast(error.message,'error');}
  };
 }catch(error){toast(error.message,'error');}
}

function defaultPeakSurchargeForRoomType(typeName){
 const key=String(typeName||'').trim().toLowerCase();
 const rates={standard:0.20,deluxe:0.25,vip:0.30,family:0.35};
 if(!(key in rates))throw new Error(`Chưa cấu hình phụ thu mùa cao điểm cho loại phòng "${typeName}".`);
 return rates[key];
}
async function openPeakSeasonBulkForm(){
 try{
  const rooms=await api('/api/rooms/');
  if(!rooms.length){toast('Khách sạn chưa có phòng để áp dụng mùa cao điểm.','error');return;}
  const roomRows=rooms.map(room=>{
   const rate=defaultPeakSurchargeForRoomType(room.ten_loai_phong);
   return `<tr><td><b>Phòng ${esc(room.so_phong)}</b><small class="muted" style="display:block">${esc(room.ten_loai_phong)} · ID: ${room.id}</small></td><td><b>${Math.round(rate*100)}%</b></td></tr>`;
  }).join('');
  const today=new Date();const dateValue=d=>[d.getFullYear(),String(d.getMonth()+1).padStart(2,'0'),String(d.getDate()).padStart(2,'0')].join('-');
  openModal('Tạo mùa cao điểm cho tất cả phòng',`
   <p class="muted" style="margin:0 0 14px">Một khoảng ngày chỉ tạo <b>một bản ghi muacaodiem</b>. Mỗi phòng được liên kết qua <b>phong_muacaodiem</b>. Tỷ lệ tự động lấy theo loại phòng của từng phòng: Standard 20%, Deluxe 25%, VIP 30%, Family 35%.</p>
   <form id="peak-season-all-form">
    <div class="form-grid">
     <div class="field"><label>Từ ngày</label><input type="date" name="tu_ngay" required></div>
     <div class="field"><label>Đến ngày</label><input type="date" name="den_ngay" required></div>
    </div>
    <div class="table-scroll" style="margin-top:16px;max-height:330px;overflow:auto"><table><thead><tr><th>Phòng / Loại phòng</th><th>Tỷ lệ phụ thu</th></tr></thead><tbody>${roomRows}</tbody></table></div>
    <p class="muted" style="font-size:11px;margin:10px 0 0">Tỷ lệ được hệ thống xác định tự động theo loại phòng đang gán cho từng phòng vật lý, không nhập mức phụ thu chung cho loại phòng.</p>
    <div class="form-actions"><button type="button" class="btn btn-secondary" data-close>Hủy</button><button class="btn btn-primary">Áp dụng cho ${rooms.length} phòng</button></div>
   </form>`);
  const form=$('#peak-season-all-form');
  form.onsubmit=async event=>{
   event.preventDefault();
   const data=new FormData(form),start=String(data.get('tu_ngay')||''),end=String(data.get('den_ngay')||'');
   if(!start||!end||end<=start){toast('Ngày kết thúc phải sau ngày bắt đầu.','error');return;}
   try{
    const result=await api('/api/peak-seasons/apply-all',{method:'POST',body:JSON.stringify({tu_ngay:start,den_ngay:end})});
    closeModal();toast(result.message||'Đã tạo mùa cao điểm với tỷ lệ theo từng loại phòng.');listPage('peak-seasons');
   }catch(error){toast(error.message,'error');}
  };
 }catch(error){toast(error.message,'error');}
}
async function removeRecord(key,id){if(!confirm(`Xóa ${cfg[key].singular} #${id}?`))return;try{await api(`${cfg[key].endpoint}${id}`,{method:'DELETE'});toast('Đã xóa dữ liệu.');listPage(key);}catch(e){toast(e.message,'error');}}
async function invoiceCreate(){try{const res=await api('/api/invoices/eligible-bookings');const rows=res.bookings||[];if(!rows.length){toast('Không có Booking đủ điều kiện lập hóa đơn.','error');return;}openModal('Lập hóa đơn từ Booking',`<form id="invoice-form"><div class="field"><label>Booking</label><select name="booking_id" required>${rows.map(b=>`<option value="${b.id}">#${b.id} · Phòng ${esc(b.so_phong)} · ${esc(b.ho_ten)} · ${esc(b.trang_thai)}</option>`).join('')}</select></div><div class="field" style="margin-top:14px"><label>Phương thức thanh toán</label><select name="method">${opts.methods.map(([v,l])=>`<option value="${v}">${l}</option>`).join('')}</select></div><div class="form-actions"><button class="btn btn-secondary" type="button" data-close>Hủy</button><button class="btn btn-primary">Lập hóa đơn & tính tiền</button></div></form>`);$('#invoice-form').onsubmit=async e=>{e.preventDefault();const d=Object.fromEntries(new FormData(e.currentTarget));d.booking_id=Number(d.booking_id);try{const result=await api('/api/invoices/',{method:'POST',body:JSON.stringify(d)});closeModal();toast(result.message||'Đã lập hóa đơn.');listPage('invoices');}catch(x){toast(x.message,'error');}};}catch(e){toast(e.message,'error');}}
async function viewInvoice(id) {
  try {
    const r = await api(`/api/invoices/${id}`);
    const inv = r.invoice || r;
    const services = (Array.isArray(inv.dich_vu_tinh_phi) ? inv.dich_vu_tinh_phi : [])
      .filter(service => Number(service.don_gia || 0) > 0 && Number(service.so_luong || 0) > 0);
    const toSurchargePercent = value => {
      let rate = Number(value);
      if (!Number.isFinite(rate) || rate <= 0) return null;
      // Legacy snapshots may store a multiplier (1.30); current snapshots store 0.30.
      if (rate > 1) rate -= 1;
      const percent = Math.round(rate * 100);
      return percent > 0 ? percent : null;
    };
    let rawSnapshot = inv.chi_tiet_mua_cao_diem || [];
    if (typeof rawSnapshot === 'string') {
      try { rawSnapshot = JSON.parse(rawSnapshot); } catch (_) { rawSnapshot = []; }
    }
    const snapshotRates = Array.isArray(rawSnapshot)
      ? rawSnapshot
          .filter(item => item && (item.mua_cao_diem_id != null || Number(item.phi_mua_cao_diem || 0) > 0))
          .map(item => toSurchargePercent(item.he_so_gia))
          .filter(rate => rate !== null)
      : [];
    const apiRates = (Array.isArray(inv.he_so_mua_cao_diem) ? inv.he_so_mua_cao_diem : [])
      .map(toSurchargePercent).filter(rate => rate !== null);
    const peakRates = [...new Set(apiRates.length ? apiRates : snapshotRates)];
    const peakLabel = peakRates.length
      ? `Phụ phí mùa cao điểm (${peakRates.map(rate => `${rate}%`).join(', ')})`
      : 'Phụ phí mùa cao điểm';
    const serviceRows = services.map(service => {
      const amount = service.thanh_tien ?? (Number(service.don_gia || 0) * Number(service.so_luong || 0));
      const quantity = Number(service.so_luong || 0);
      const unit = service.don_vi_tinh ? ` ${esc(service.don_vi_tinh)}` : '';
      return `<tr><td>${esc(service.ten)}</td><td>${money(service.don_gia)}</td><td>${quantity}${unit}</td><td>${money(amount)}</td></tr>`;
    }).join('');
    const serviceDetailMarkup = services.length
      ? `<section class="invoice-services"><h4>CHI TIẾT DỊCH VỤ TÍNH PHÍ</h4><div class="table-scroll"><table><thead><tr><th>Dịch vụ</th><th>Đơn giá</th><th>Số lượng</th><th>Thành tiền</th></tr></thead><tbody>${serviceRows}</tbody></table></div></section>`
      : `<section class="invoice-services"><h4>CHI TIẾT DỊCH VỤ TÍNH PHÍ</h4><p>${Number(inv.tien_dich_vu || 0) > 0 ? 'Hóa đơn có tiền dịch vụ nhưng API chưa trả về từng dòng dịch vụ. Hãy tải lại Backend và kiểm tra dữ liệu dichvu theo Booking.' : 'Không có dịch vụ tính phí được ghi nhận cho Booking này.'}</p></section>`;

    const summaryRows = [
      ['Mã hóa đơn', inv.id],
      ['Mã thanh toán', inv.pay_id],
      ['Tiền phòng', money(inv.tien_phong)],
      [peakLabel, money(inv.tien_phu_phi_mua_cao_diem)],
      ['Tiền dịch vụ', money(inv.tien_dich_vu)],
      ['TỔNG TIỀN', money(inv.tong_tien)],
    ];
    openModal(`Hóa đơn #${id}`, `<div class="invoice-summary">${summaryRows.map(([k,v],i)=>`<div class="summary-row ${i===summaryRows.length-1?'total':''}"><span>${esc(k)}</span><b>${esc(v)}</b></div>`).join('')}</div>${serviceDetailMarkup}<div class="form-actions"><button class="btn btn-primary" id="print-invoice">In / Lưu PDF</button></div>`);

    $('#print-invoice').onclick = () => {
      const w = window.open('', '_blank');
      if (!w) {
        toast('Trình duyệt đã chặn cửa sổ in hóa đơn. Hãy cho phép cửa sổ bật lên rồi thử lại.', 'error');
        return;
      }
      const printServiceRows = services.map(service => {
        const amount = service.thanh_tien ?? (Number(service.don_gia || 0) * Number(service.so_luong || 0));
        const quantity = Number(service.so_luong || 0);
        const unit = service.don_vi_tinh ? ` ${esc(service.don_vi_tinh)}` : '';
        return `<tr><td>${esc(service.ten)}</td><td>${money(service.don_gia)}</td><td>${quantity}${unit}</td><td>${money(amount)}</td></tr>`;
      }).join('');
      const servicePrintBlock = services.length
        ? `<h2>CHI TIẾT DỊCH VỤ TÍNH PHÍ</h2><table class="service-table"><thead><tr><th>Dịch vụ</th><th>Đơn giá</th><th>Số lượng</th><th>Thành tiền</th></tr></thead><tbody>${printServiceRows}</tbody></table>`
        : `<h2>CHI TIẾT DỊCH VỤ TÍNH PHÍ</h2><p>Không có dịch vụ tính phí được ghi nhận cho Booking này.</p>`;
      const printRows = [
        ['Mã thanh toán', inv.pay_id],
        ['Tiền phòng', money(inv.tien_phong)],
        [peakLabel, money(inv.tien_phu_phi_mua_cao_diem)],
        ['Tiền dịch vụ', money(inv.tien_dich_vu)],
        ['TỔNG TIỀN', money(inv.tong_tien)],
      ];
      w.document.write(`<html><head><meta charset="UTF-8"><title>Hóa đơn ${id}</title><style>
        body{font:15px Arial,sans-serif;padding:40px;color:#20364a}h1{text-align:center;margin-bottom:28px}
        h2{font-size:16px;margin:28px 0 10px}p{margin:14px 0}
        table{width:100%;border-collapse:collapse;margin-top:18px}th,td{padding:11px 12px;border-bottom:1px solid #ddd;text-align:left}
        td:last-child,th:last-child{text-align:right;font-weight:bold}.summary-table td:first-child{width:70%}
        .total{font-size:20px}.service-table{font-size:13px}.service-table th{background:#f5f7fa}
        @media print{body{padding:15mm}}
      </style></head><body><h1>HÓA ĐƠN THANH TOÁN</h1><p>Mã hóa đơn: #${esc(inv.id)}</p><table class="summary-table">${printRows.map(([k,v],i)=>`<tr class="${i===printRows.length-1?'total':''}"><td>${esc(k)}</td><td>${esc(v)}</td></tr>`).join('')}</table>${servicePrintBlock}</body></html>`);
      w.document.close();
      w.focus();
      w.print();
    };
  } catch (e) {
    toast(e.message, 'error');
  }
}
async function webhookList(){try{const d=await api('/api/payments/webhook-events');openModal('Nhật ký giao dịch QR / SePay',miniTable(d.events||[],[['id','ID'],['transaction_id','Transaction'],['payment_code','Mã thanh toán'],['transfer_amount','Số tiền'],['processing_result','Kết quả'],['received_at','Thời điểm']]));}catch(e){toast(e.message,'error');}}
async function reportsPage(){const c=$('#content');const now=new Date(),from=new Date(now.getFullYear(),now.getMonth(),1);c.innerHTML=`<div class="page-heading"><div><div class="eyebrow">ANALYTICS</div><h1>Báo cáo doanh thu</h1><p>Thống kê giao dịch theo khoảng thời gian.</p></div></div><div class="panel"><form id="report-form" class="form-grid"><div class="field"><label>Từ ngày</label><input type="date" name="tu_ngay" value="${[from.getFullYear(),String(from.getMonth()+1).padStart(2,'0'),String(from.getDate()).padStart(2,'0')].join('-')}" required></div><div class="field"><label>Đến ngày</label><input type="date" name="den_ngay" value="${[now.getFullYear(),String(now.getMonth()+1).padStart(2,'0'),String(now.getDate()).padStart(2,'0')].join('-')}" required></div><div class="full"><button class="btn btn-primary">Xem báo cáo</button></div></form></div><div id="report-results" style="margin-top:18px"></div>`;$('#report-form').onsubmit=async e=>{e.preventDefault();const d=Object.fromEntries(new FormData(e.currentTarget));try{const r=await api(`/api/reports/revenue?tu_ngay=${d.tu_ngay}&den_ngay=${d.den_ngay}`);$('#report-results').innerHTML=`<div class="stats-grid"><div class="stat-card"><div class="stat-label">Doanh thu thực thu</div><div class="stat-value">${money(r.data?.[0]?.doanh_thu_thuc_thu??r.doanh_thu_thuc_thu??r.tong_doanh_thu??0)}</div></div><div class="stat-card"><div class="stat-label">Giao dịch thành công</div><div class="stat-value">${r.data?.[0]?.so_giao_dich_thanh_cong??r.so_giao_dich_thanh_cong??0}</div></div><div class="stat-card"><div class="stat-label">Tổng tiền hoàn</div><div class="stat-value">${money(r.data?.[0]?.tong_tien_hoan??r.tong_tien_hoan??0)}</div></div><div class="stat-card"><div class="stat-label">Số giao dịch hoàn</div><div class="stat-value">${r.data?.[0]?.so_giao_dich_hoan_tien??r.so_giao_dich_hoan_tien??0}</div></div></div><div class="panel"><h3 class="panel-title">Chi tiết báo cáo</h3><pre style="white-space:pre-wrap;font:12px/1.6 monospace;color:#506477">${esc(JSON.stringify(r,null,2))}</pre></div>`;}catch(x){toast(x.message,'error');}};$('#report-form').requestSubmit();}

function peakRateText(record){
 let nights=record?.chi_tiet_mua_cao_diem||[];
 if(typeof nights==='string'){try{nights=JSON.parse(nights);}catch(_){nights=[];}}
 const rates=[...new Set((Array.isArray(nights)?nights:[])
  .filter(n=>n&&n.mua_cao_diem_id!=null&&Number(n.phi_mua_cao_diem||0)>0)
  .map(n=>{let rate=Number(n.he_so_gia||0);if(rate>1)rate-=1;return Math.round(rate*100);})
  .filter(rate=>rate>0))].sort((a,b)=>a-b);
 return rates.length?rates.map(rate=>`${rate}%`).join(', '):'';
}

async function customerHome() {
    const c = $('#content');

    // Ngày hiện tại và ngày tiếp theo
    const localDate = d => [
        d.getFullYear(),
        String(d.getMonth() + 1).padStart(2, '0'),
        String(d.getDate()).padStart(2, '0')
    ].join('-');

    const todayDate = new Date();
    const tomorrowDate = new Date(todayDate);
    tomorrowDate.setDate(tomorrowDate.getDate() + 1);

    const today = localDate(todayDate);
    const tomorrow = localDate(tomorrowDate);

    // Tải danh sách loại phòng từ API Customer
    let roomTypes = [];

    try {
        roomTypes = await api('/api/customer/room-types');
    } catch (e) {
        c.innerHTML = `
            <div class="empty panel">
                Không tải được danh sách loại phòng:
                ${esc(e.message)}
            </div>`;
        return;
    }

    if (!Array.isArray(roomTypes) || roomTypes.length === 0) {
        c.innerHTML = `
            <div class="empty panel">
                Hiện chưa có loại phòng để đặt.
                Vui lòng liên hệ khách sạn.
            </div>`;
        return;
    }

    // Ánh xạ tên loại phòng với ảnh tương ứng
    const imageSlug = (name, id) => {
        const key = String(name || '')
            .normalize('NFD')
            .replace(/[\u0300-\u036f]/g, '')
            .toLowerCase()
            .trim();

        if (key.includes('standard')) return 'standard';
        if (key.includes('deluxe')) return 'deluxe';
        if (key.includes('vip')) return 'vip';
        if (key.includes('family')) return 'family';

        return `room-type-${id}`;
    };

    // Ảnh được FastAPI phục vụ trực tiếp từ thư mục Hotel_project5/images.
    // Giữ placeholder làm dự phòng nếu thiếu ảnh hoặc tên file không khớp.
    const imageMarkup = t => {
        const slug = imageSlug(t.ten, t.id);
        const imagePath = `/images/${slug}.jpg`;

        return `
            <div class="room-type-image-placeholder">
                <img
                    class="room-type-photo"
                    src="${imagePath}"
                    alt="Ảnh loại phòng ${esc(t.ten)}"
                    loading="lazy"
                    onload="this.nextElementSibling.hidden=true"
                    onerror="this.hidden=true;this.nextElementSibling.hidden=false"
                >

                <div class="room-type-image-placeholder-inner" hidden>
                    <span class="room-type-image-icon">▧</span>
                    <strong>Ảnh ${esc(t.ten)}</strong>
                    <small>Chưa có ảnh cho loại phòng này</small>
                </div>
            </div>
        `;
    };

    // Danh sách dịch vụ mặc định của từng loại phòng
    const serviceMarkup = t => {
        const services = Array.isArray(t.dich_vu_mac_dinh)
            ? t.dich_vu_mac_dinh
            : Array.isArray(t.default_services)
                ? t.default_services
                : [];

        if (services.length === 0) {
            return `
                <div class="room-type-no-services">
                    Chưa cấu hình dịch vụ mặc định
                </div>
            `;
        }

        return `
            <ul class="room-type-services">
                ${services.map(service => {
                    const price = Number(service.don_gia || 0) === 0
                        ? 'Miễn phí'
                        : money(service.don_gia);

                    const appliedRooms = Number(
                        service.so_phong_co_dich_vu ?? service.so_phong_ap_dung ?? 0
                    );
                    const roomCount = `${appliedRooms}/${Number(t.so_phong || 0)} phòng`;
                    const qtyMin = Number(service.so_luong_min ?? service.so_luong ?? 1);
                    const qtyMax = Number(service.so_luong_max ?? qtyMin);
                    const quantityText = qtyMin === qtyMax
                        ? `${qtyMin} phần/phòng`
                        : `${qtyMin}–${qtyMax} phần/phòng`;

                    return `
                        <li>
                            <span class="room-service-name">
                                ${esc(service.ten)}
                            </span>
                            <span class="room-service-meta">
                                ${price} · ${roomCount} · ${quantityText}
                            </span>
                        </li>
                    `;
                }).join('')}
            </ul>
        `;
    };

    // Giao diện Customer Portal
    c.innerHTML = `
        <div class="welcome-card">
            <div>
                <div class="eyebrow">YOUR STAY, YOUR WAY</div>
                <h2>
                    Xin chào,
                    ${esc(state.user.full_name || 'Quý khách')}!
                </h2>
                <p>
                    Tìm phòng phù hợp, xem giá và dịch vụ
                    mặc định trước khi đặt phòng.
                </p>
            </div>
            <div class="welcome-art">⌂</div>
        </div>

        <div class="page-heading">
            <div>
                <h1>Chọn loại phòng</h1>
                <p>
                    Xem hình ảnh, giá, sức chứa và dịch vụ mặc định
                    trước khi tìm phòng khả dụng.
                </p>
                <p class="room-type-help">
                    Dịch vụ mặc định do khách sạn cấu hình theo từng loại phòng
                    và được đồng bộ cho các phòng thuộc loại đó.
                </p>
            </div>
        </div>

        <!-- BỐ CỤC 4 THẺ: 2 CỘT x 2 HÀNG -->
        <section
            id="customer-room-type-grid"
            class="room-type-grid"
            aria-label="Danh sách loại phòng"
        >
            ${roomTypes.map(t => `
                <article
                    class="room-type-card"
                    data-room-type-card="${Number(t.id)}"
                >
                    ${imageMarkup(t)}

                    <div class="room-type-card-body">

                        <div class="room-type-card-top">
                            <span class="room-type-kicker">
                                LOẠI PHÒNG
                            </span>
                            <span class="badge blue">
                                ${Number(t.so_phong || 0)} phòng
                            </span>
                        </div>

                        <h2>${esc(t.ten)}</h2>

                        <div class="room-type-price">
                            ${money(t.gia_co_ban)}
                            <small>/ đêm</small>
                        </div>

                        <div class="room-type-facts">
                            <span>Sức chứa tối đa</span>
                            <b>${Number(t.suc_chua || 0)} khách</b>
                        </div>

                        <div class="room-type-services-title">
                            Dịch vụ mặc định
                        </div>

                        ${serviceMarkup(t)}

                        <button
                            type="button"
                            class="btn btn-outline room-type-select"
                            data-select-room-type="${Number(t.id)}"
                        >
                            Chọn loại phòng này
                        </button>

                    </div>
                </article>
            `).join('')}
        </section>

        <!-- CHỌN NGÀY SAU KHI CHỌN LOẠI PHÒNG -->
        <section
            id="customer-date-panel"
            class="panel customer-date-panel"
            hidden
        >
            <div class="panel-head">
                <div>
                    <h3 class="panel-title">
                        Chọn ngày lưu trú
                    </h3>
                    <p
                        class="muted"
                        id="customer-selected-type-label"
                        style="font-size:12px;margin:4px 0 0"
                    ></p>
                </div>
                <span class="badge green">
                    Đã chọn loại phòng
                </span>
            </div>

            <form id="room-search" class="form-grid">

                <input
                    type="hidden"
                    name="loai_phong_id"
                    id="customer-room-type"
                >

                <div class="field">
                    <label>Ngày nhận phòng</label>
                    <input
                        name="ngay_nhan"
                        type="date"
                        value="${today}"
                        min="${today}"
                        required
                    >
                </div>

                <div class="field">
                    <label>Ngày trả phòng</label>
                    <input
                        name="ngay_tra"
                        type="date"
                        value="${tomorrow}"
                        min="${tomorrow}"
                        required
                    >
                </div>

                <div class="full">
                    <button class="btn btn-primary" type="submit">
                        Tìm phòng khả dụng →
                    </button>
                </div>
            </form>
        </section>

        <div id="room-results" style="margin-top:20px"></div>
    `;

    // Xử lý chọn loại phòng
    let selectedType = null;

    const datePanel = $('#customer-date-panel');

    const clearResults = () => {
        $('#room-results').innerHTML = '';
    };

    $$('[data-select-room-type]').forEach(button => {
        button.onclick = () => {
            const id = Number(button.dataset.selectRoomType);

            selectedType = roomTypes.find(
                t => Number(t.id) === id
            );

            if (!selectedType) return;

            $('#customer-room-type').value =
                String(selectedType.id);

            $('#customer-selected-type-label').textContent =
                `${selectedType.ten} · ` +
                `${money(selectedType.gia_co_ban)}/đêm · ` +
                `${Number(selectedType.suc_chua || 0)} khách`;

            // Đánh dấu thẻ đang chọn
            $$('[data-room-type-card]').forEach(card => {
                const active =
                    Number(card.dataset.roomTypeCard) === id;

                card.classList.toggle('selected', active);

                const selectButton =
                    card.querySelector('[data-select-room-type]');

                if (selectButton) {
                    selectButton.classList.toggle(
                        'btn-primary', active
                    );
                    selectButton.classList.toggle(
                        'btn-outline', !active
                    );

                    selectButton.textContent = active
                        ? 'Đã chọn loại phòng ✓'
                        : 'Chọn loại phòng này';
                }
            });

            clearResults();
            datePanel.hidden = false;

            datePanel.scrollIntoView({
                behavior: 'smooth',
                block: 'nearest'
            });
        };
    });

    // Kiểm tra ngày nhận và ngày trả
    const checkIn = $('input[name="ngay_nhan"]');
    const checkOut = $('input[name="ngay_tra"]');

    checkIn.onchange = () => {
        const nextDay = new Date(`${checkIn.value}T00:00:00`);
        nextDay.setDate(nextDay.getDate() + 1);

        const minCheckout = localDate(nextDay);

        checkOut.min = minCheckout;

        if (!checkOut.value || checkOut.value <= checkIn.value) {
            checkOut.value = minCheckout;
        }

        clearResults();
    };

    checkOut.onchange = clearResults;

    // Tìm phòng khả dụng theo loại phòng đã chọn
    $('#room-search').onsubmit = async e => {
        e.preventDefault();

        const d = Object.fromEntries(
            new FormData(e.currentTarget)
        );

        if (
            !selectedType ||
            Number(d.loai_phong_id) !== Number(selectedType.id)
        ) {
            toast(
                'Vui lòng chọn loại phòng trước.',
                'error'
            );
            return;
        }

        if (d.ngay_tra <= d.ngay_nhan) {
            toast(
                'Ngày trả phải sau ngày nhận.',
                'error'
            );
            return;
        }

        $('#room-results').innerHTML = `
            <div class="loading-line">
                Đang tìm phòng thuộc loại đã chọn…
            </div>
        `;

        try {
            const url =
                `/api/customer/available-rooms` +
                `?ngay_nhan=${encodeURIComponent(d.ngay_nhan)}` +
                `&ngay_tra=${encodeURIComponent(d.ngay_tra)}` +
                `&loai_phong_id=${encodeURIComponent(d.loai_phong_id)}`;

            const r = await api(url);

            state.cache.customerDates = {
                ngay_nhan: d.ngay_nhan,
                ngay_tra: d.ngay_tra,
                loai_phong_id: Number(d.loai_phong_id)
            };

            const rooms = r.rooms || [];

            $('#room-results').innerHTML = `
                <div class="panel" style="margin-bottom:15px">
                    <div class="panel-head" style="margin-bottom:7px">
                        <h3 class="panel-title">
                            ${esc(selectedType.ten)}
                        </h3>
                        <span class="badge blue">
                            ${rooms.length} phòng khả dụng
                        </span>
                    </div>

                    <div class="muted" style="font-size:12px">
                        ${money(selectedType.gia_co_ban)} / đêm ·
                        Sức chứa ${selectedType.suc_chua} khách ·
                        ${d.ngay_nhan} → ${d.ngay_tra}
                    </div>
                </div>

                ${rooms.length ? `
                    <div class="room-grid">
                        ${rooms.map(room => `
                            <article class="room-card">
                                <span class="badge green">
                                    Có thể đặt
                                </span>

                                <h3>
                                    Phòng ${esc(
                                        room.so_phong || room.phong_id
                                    )}
                                </h3>

                                <p class="muted" style="font-size:12px">
                                    ${esc(
                                        room.loai_phong || selectedType.ten
                                    )}
                                    · Tối đa
                                    ${room.suc_chua ?? selectedType.suc_chua}
                                    khách
                                </p>

                                <div class="price">
                                    ${money(
                                        room.tong_tien_phong_va_phu_phi
                                    )}
                                </div>

                                <div class="muted" style="font-size:11px">
                                    Tiền phòng:
                                    ${money(room.tien_phong_du_kien)}
                                    · Phụ phí mùa cao điểm${peakRateText(room)?` (${esc(peakRateText(room))})`:''}:
                                    ${money(
                                        room.tien_phu_phi_mua_cao_diem
                                    )}
                                </div>

                                <button
                                    class="btn btn-primary"
                                    style="width:100%;margin-top:15px"
                                    data-select-room="${room.phong_id || room.id}"
                                >
                                    Chọn phòng này
                                </button>
                            </article>
                        `).join('')}
                    </div>
                ` : `
                    <div class="empty panel">
                        Không còn phòng thuộc loại này
                        trong khoảng ngày đã chọn.
                        Bạn hãy đổi ngày hoặc chọn loại phòng khác.
                    </div>
                `}
            `;

            $$('[data-select-room]').forEach(button => {
                button.onclick = () => {
                    chooseCustomerRoom(
                        Number(button.dataset.selectRoom),
                        {
                            ngay_nhan: d.ngay_nhan,
                            ngay_tra: d.ngay_tra
                        }
                    );
                };
            });

        } catch (x) {
            $('#room-results').innerHTML = `
                <div class="empty panel">
                    ${esc(x.message)}
                </div>
            `;
        }
    };
}

async function chooseCustomerRoom(roomId,dates){
 try{
  const [s,p]=await Promise.all([
   api(`/api/customer/rooms/${roomId}/services`),
   api(`/api/customer/rooms/${roomId}/price-preview?ngay_nhan=${dates.ngay_nhan}&ngay_tra=${dates.ngay_tra}`)
  ]);
  const defaults=s.default_services||s.services||[];
  const addons=s.addon_services||[];
  const defaultMarkup=defaults.length?defaults.map(x=>`
   <div class="service-option">
    <label><input type="checkbox" name="service-${x.dichvu_id}" checked>
     <span><b>${esc(x.ten)}</b><br><small class="muted">Miễn phí · ${Number(x.so_luong)} ${esc(x.don_vi_tinh||'phần')}</small></span>
    </label>
    <input aria-label="Số lượng ${esc(x.ten)}" type="number" min="1" max="99" value="${x.so_luong}" name="qty-${x.dichvu_id}" style="width:76px;padding:7px;border:1px solid var(--line);border-radius:7px">
   </div>`).join(''):'<div class="empty">Phòng này chưa có dịch vụ mặc định.</div>';
  const addonGroupNames={AN_SANG:'Ăn sáng',GIUONG_PHU:'Giường phụ',GIAT_UI:'Giặt ủi',MINIBAR:'Minibar',DUA_DON:'Đưa đón sân bay',TRANG_TRI:'Trang trí phòng',KHAC:'Dịch vụ khác'};
  const groupedAddons=addons.reduce((groups,item)=>{const key=item.nhom_dich_vu||'KHAC';(groups[key]??=[]).push(item);return groups;},{});
  const addonMarkup=addons.length?Object.entries(groupedAddons).map(([group,items])=>`
   <section class="paid-service-group"><h5>${esc(addonGroupNames[group]||group)}</h5>${items.map(x=>{
    const unit=x.don_vi_tinh||'lần';
    const detail=unit==='giường/đêm'?'Số giường phụ mỗi đêm':unit==='suất/buổi'?'Số suất ăn':'Số lượng ('+unit+')';
    return `<div class="paid-service-row">
     <label class="paid-service-choice"><input type="checkbox" name="addon-${x.dichvu_id}">
      <span><b>${esc(x.ten)}</b><small>${money(x.don_gia)} / ${esc(unit)} · chỉ tính khi chọn</small></span>
     </label>
     <div class="paid-service-quantity"><label>${detail}</label><input type="number" min="1" max="99" step="1" value="${Number(x.so_luong)||1}" name="qty-${x.dichvu_id}" data-addon-qty="${x.dichvu_id}" data-price="${Number(x.don_gia)}" data-unit="${esc(unit)}" disabled></div>
    </div>`;
   }).join('')}</section>`).join(''):'<div class="empty">Chưa có dịch vụ bổ sung đang kinh doanh.</div>';
  openModal(`Chọn dịch vụ · Phòng ${s.phong.so_phong}`,`
   <form id="customer-book-form">
    <div class="invoice-summary" style="margin-bottom:16px">
     <div class="summary-row"><span>Số đêm</span><b>${p.so_dem}</b></div>
     <div class="summary-row"><span>Tiền phòng</span><b>${money(p.tien_phong_du_kien)}</b></div>
     <div class="summary-row"><span>Phụ phí mùa cao điểm${peakRateText(p)?` (${esc(peakRateText(p))})`:''}</span><b>${money(p.tien_phu_phi_mua_cao_diem)}</b></div>
     <div class="summary-row total"><span>Tiền phòng + phụ phí</span><b>${money(p.tong_tien_phong_va_phu_phi)}</b></div>
    </div>
    <h4 class="service-section-title">Dịch vụ mặc định miễn phí</h4>
    <p class="muted service-section-note">Các dịch vụ được chọn sẵn. Bạn có thể bỏ chọn hoặc thay đổi số lượng nhận.</p>
    ${defaultMarkup}
    <h4 class="service-section-title paid-title">Dịch vụ bổ sung tính phí</h4>
    <p class="muted service-section-note">Không có dịch vụ nào được chọn sẵn. Chỉ dịch vụ bạn tích chọn mới được tính vào hóa đơn.</p>
    ${addonMarkup}
    <div class="paid-service-total"><span>Tạm tính dịch vụ bổ sung</span><b id="addon-estimate">0 ₫</b></div>
    <p class="muted service-section-note">Giường phụ được tính theo số giường mỗi đêm × số đêm lưu trú. Các dịch vụ khác tính theo số lượng bạn chọn.</p>
    <div class="form-actions"><button type="button" class="btn btn-secondary" data-close>Quay lại</button><button class="btn btn-primary">Xác nhận đặt phòng</button></div>
   </form>`);
  const form=$('#customer-book-form');
  const updateAddonTotal=()=>{
   let total=0;
   addons.forEach(x=>{
    const checked=form.querySelector(`[name="addon-${x.dichvu_id}"]`)?.checked;
    const qty=form.querySelector(`[name="qty-${x.dichvu_id}"]`);
    if(!qty)return;
    qty.disabled=!checked;
    if(checked){let amount=Math.max(1,Number(qty.value)||1);if(qty.dataset.unit==='giường/đêm')amount*=Number(p.so_dem||1);total+=amount*Number(x.don_gia||0);}
   });
   const output=$('#addon-estimate');if(output)output.textContent=money(total);
  };
  form.addEventListener('change',updateAddonTotal);
  form.addEventListener('input',updateAddonTotal);
  updateAddonTotal();
  form.onsubmit=async e=>{
   e.preventDefault();
   const f=new FormData(form);
   const selectedDefaults=defaults.filter(x=>f.has(`service-${x.dichvu_id}`)).map(x=>({dichvu_id:x.dichvu_id,so_luong:Number(f.get(`qty-${x.dichvu_id}`)||1)}));
   const selectedAddons=addons.filter(x=>f.has(`addon-${x.dichvu_id}`)).map(x=>({dichvu_id:x.dichvu_id,so_luong:Number(f.get(`qty-${x.dichvu_id}`)||1)}));
   const dich_vu=[...selectedDefaults,...selectedAddons];
   try{
    const r=await api('/api/customer/bookings',{method:'POST',body:JSON.stringify({phong_id:roomId,ngay_nhan:dates.ngay_nhan,ngay_tra:dates.ngay_tra,dich_vu})});
    closeModal();
    toast(`Đặt phòng thành công · Booking #${r.booking_id} · Dịch vụ ${money(r.tong_tien_dich_vu||0)}`);
    go('my-bookings');
   }catch(x){toast(x.message,'error');}
  };
 }catch(e){toast(e.message,'error');}
}
async function myBookings(){const c=$('#content');c.innerHTML=`<div class="page-heading"><div><div class="eyebrow">MY RESERVATIONS</div><h1>Booking của tôi</h1><p>Theo dõi trạng thái đặt phòng và yêu cầu thanh toán.</p></div><button class="btn btn-primary" id="find-room">＋ Đặt phòng mới</button></div><div id="my-bookings" class="loading-line">Đang tải…</div>`;$('#find-room').onclick=()=>go('customer-home');try{const r=await api('/api/customer/bookings');const rows=r.bookings||[];$('#my-bookings').innerHTML=rows.length?`<div class="grid">${rows.map(b=>`<article class="panel"><div class="panel-head"><div><div class="eyebrow">BOOKING #${b.booking_id}</div><h3 class="panel-title">Phòng ${esc(b.so_phong)} · ${esc(b.loai_phong)}</h3></div>${badge(b.trang_thai)}</div><div class="grid three-col"><div><small class="muted">Thời gian lưu trú</small><p><b>${dateText(b.ngay_nhan)} → ${dateText(b.ngay_tra)}</b></p></div><div><small class="muted">Tiền phòng</small><p><b>${money(b.tien_phong_du_kien)}</b></p></div><div><small class="muted">Phụ phí mùa cao điểm</small><p><b>${money(b.tien_phu_phi_mua_cao_diem)}</b></p></div></div><div class="actions" style="margin-top:12px">${['DA_XAC_NHAN','DANG_O','HOAN_THANH'].includes(b.trang_thai)?`<button class="btn btn-primary btn-sm" data-pay-booking="${b.booking_id}">Thanh toán / Hóa đơn</button>`:''}${!['DA_HUY','HOAN_THANH'].includes(b.trang_thai)?`<button class="btn btn-danger btn-sm" data-cancel-booking="${b.booking_id}">Hủy Booking</button>`:''}</div></article>`).join('')}</div>`:'<div class="empty panel">Bạn chưa có Booking nào. Hãy tìm phòng để bắt đầu.</div>';$$('[data-pay-booking]').forEach(b=>b.onclick=()=>customerPay(Number(b.dataset.payBooking)));$$('[data-cancel-booking]').forEach(b=>b.onclick=()=>cancelCustomerBooking(Number(b.dataset.cancelBooking)));}catch(e){$('#my-bookings').innerHTML=`<div class="empty">${esc(e.message)}</div>`;}}
async function cancelCustomerBooking(id){if(!confirm(`Bạn muốn hủy Booking #${id}?`))return;try{await api(`/api/customer/bookings/${id}/cancel`,{method:'POST',body:'{}'});toast('Đã gửi yêu cầu hủy Booking.');myBookings();}catch(e){toast(e.message,'error');}}
async function customerPay(id){openModal(`Thanh toán Booking #${id}`,`<form id="customer-pay-form"><div class="field"><label>Phương thức thanh toán</label><select name="method"><option value="CHUYEN_KHOAN">Chuyển khoản QR</option><option value="TIEN_MAT">Tiền mặt tại quầy</option><option value="THE">Thẻ</option></select></div><p class="muted" style="font-size:11px;margin-top:12px">Booking cần được khách sạn xác nhận trước khi yêu cầu thanh toán.</p><div class="form-actions"><button type="button" class="btn btn-secondary" data-close>Đóng</button><button class="btn btn-primary">Tạo yêu cầu thanh toán</button></div></form>`);$('#customer-pay-form').onsubmit=async e=>{e.preventDefault();const method=new FormData(e.currentTarget).get('method');try{const r=await api(`/api/customer/bookings/${id}/payment`,{method:'POST',body:JSON.stringify({method})});closeModal();if(method==='CHUYEN_KHOAN'&&r.invoice?.pay_id){await showQr(r.invoice.pay_id);}else{toast(r.message||'Đã tạo yêu cầu thanh toán.');myBookings();}}catch(x){toast(x.message,'error');}};}
async function showQr(payId){try{const q=await api(`/api/customer/payments/${payId}/qr`);openModal(`Thanh toán QR · Pay #${payId}`,`<div style="display:grid;justify-items:center;gap:10px;text-align:center"><h3 style="font:800 22px Manrope;margin:0">${money(q.amount)}</h3><p class="muted" style="font-size:12px">Ngân hàng: ${esc(q.bank_code)} · ${esc(q.account_name)}</p><p class="muted" style="font-size:12px">Số tài khoản: <b>${esc(q.account_number)}</b></p><img class="qr-img" src="${esc(q.qr_url)}" alt="QR thanh toán"><div class="badge blue">Nội dung: ${esc(q.payment_code)}</div><p class="muted" style="font-size:11px">Giữ nguyên nội dung chuyển khoản để hệ thống tự đối soát.</p><button class="btn btn-outline" id="check-pay-status">Kiểm tra trạng thái thanh toán</button></div>`);$('#check-pay-status').onclick=async()=>{try{const s=await api(`/api/customer/payments/${payId}/status`);toast(`Trạng thái: ${s.payment.status}`);if(s.payment.status==='THANH_CONG'){closeModal();myBookings();}}catch(e){toast(e.message,'error');}};}catch(e){toast(e.message,'error');}}
async function myInvoices(){const c=$('#content');c.innerHTML=`<div class="page-heading"><div><div class="eyebrow">MY DOCUMENTS</div><h1>Hóa đơn của tôi</h1><p>Tra cứu hóa đơn và chi tiết các khoản thanh toán.</p></div></div><div id="my-invoices" class="loading-line">Đang tải…</div>`;try{const r=await api('/api/customer/invoices'),rows=r.invoices||[];$('#my-invoices').innerHTML=rows.length?`<div class="table-panel"><div class="table-scroll"><table><thead><tr><th>Hóa đơn</th><th>Booking</th><th>Phòng</th><th>Tiền phòng</th><th>Phụ phí mùa cao điểm</th><th>Dịch vụ</th><th>Tổng tiền</th><th>Thanh toán</th></tr></thead><tbody>${rows.map(x=>`<tr><td>#${x.hoa_don_id}</td><td>#${x.booking_id}</td><td>${esc(x.so_phong)}</td><td>${money(x.tien_phong)}</td><td>${money(x.tien_phu_phi_mua_cao_diem)}</td><td>${money(x.tien_dich_vu)}</td><td><b>${money(x.tong_tien)}</b></td><td>${badge(x.trang_thai_thanh_toan)}</td></tr>`).join('')}</tbody></table></div></div>`:'<div class="empty panel">Chưa có hóa đơn.</div>';}catch(e){$('#my-invoices').innerHTML=`<div class="empty">${esc(e.message)}</div>`;}}
async function init(){if(!state.token){authScreen();return;}try{const r=await api('/api/auth/me');state.user=r.user||state.user;renderShell();}catch(e){state.token='';state.user=null;localStorage.removeItem('hotel_token');localStorage.removeItem('hotel_user');authScreen();}}
window.addEventListener('DOMContentLoaded',init);
