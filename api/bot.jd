let store = {
    botToken: '',
    activationPassword: 'F5M-TEAM',
    maxUsers: 1000,
    activeUsers: [],
    botActive: true
};

export default async function handler(req, res) {
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
    
    if (req.method === 'OPTIONS') {
        return res.status(200).end();
    }
    
    const { command, adminCode, data, userId, message } = req.body;
    
    // التحقق من كود المدير للأوامر الحساسة
    const isAdmin = adminCode === 'F5M-TEAM';
    
    switch(command) {
        case 'sync':
            if(isAdmin && data) {
                store = { ...store, ...data };
                return res.status(200).json({ success: true });
            }
            break;
            
        case 'getData':
            if(isAdmin) {
                return res.status(200).json({ success: true, data: store });
            }
            break;
            
        case 'activate':
            const { password, username, chatId } = req.body;
            
            if(password !== store.activationPassword) {
                await sendMessage(chatId, '❌ كلمة السر غير صحيحة!');
                return res.status(200).json({ success: false, message: 'wrong_password' });
            }
            
            if(store.activeUsers.length >= store.maxUsers) {
                await sendMessage(chatId, `⚠️ عذراً! البوت وصل للحد الأقصى (${store.maxUsers}) مستخدم`);
                return res.status(200).json({ success: false, message: 'max_reached' });
            }
            
            const exists = store.activeUsers.find(u => u.id === chatId);
            if(!exists) {
                store.activeUsers.push({
                    id: chatId,
                    username: username || 'مستخدم',
                    activatedAt: new Date().toISOString()
                });
                await sendMessage(chatId, `✅ تم تفعيل البوت بنجاح!\nالمستخدمين المفعلين: ${store.activeUsers.length}/${store.maxUsers}`);
                return res.status(200).json({ success: true });
            } else {
                await sendMessage(chatId, '✅ البوت مفعل بالفعل!');
                return res.status(200).json({ success: true });
            }
            
        case 'sendMessage':
            if(isAdmin && message && userId) {
                await sendMessage(userId, message);
                return res.status(200).json({ success: true });
            }
            break;
            
        case 'broadcast':
            if(isAdmin && message) {
                let sent = 0;
                for(const user of store.activeUsers) {
                    await sendMessage(user.id, `📢 إشعار من المدير:\n\n${message}`);
                    await new Promise(r => setTimeout(r, 100));
                    sent++;
                }
                return res.status(200).json({ success: true, sent });
            }
            break;
    }
    
    return res.status(200).json({ success: false });
}

async function sendMessage(chatId, text) {
    const token = store.botToken;
    if(!token) return false;
    
    try {
        const response = await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ chat_id: chatId, text, parse_mode: 'HTML' })
        });
        return response.ok;
    } catch(e) {
        return false;
    }
}
