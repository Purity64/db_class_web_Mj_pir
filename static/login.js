document.getElementById('form-login').addEventListener('submit', async (e) => {
  e.preventDefault();

  const email = document.getElementById('login-email').value;
  const password = document.getElementById('login-password').value;

  try {
    const response = await fetch('/api/signin', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ email, password })
    });

    const result = await response.json();

    if (response.ok && result.ok) {
      alert('เข้าสู่ระบบสำเร็จ!');
      location.href = '/home';
    }else {
        alert((result.todo ? "🚧 " : "⚠️ ") + (result.error || 'เกิดข้อผิดพลาดในการเข้าสู่ระบบ'));
    }
  } catch (error) {
    console.error('Error:', error);
    alert('ไม่สามารถเชื่อมต่อกับเซิร์ฟเวอร์ได้');
  }
});


document.getElementById('form-register').addEventListener('submit', async (e) => {
  e.preventDefault();

  const name = document.getElementById('reg-name').value;
  const email = document.getElementById('reg-email').value;
  const password = document.getElementById('reg-password').value;

  try {
    const response = await fetch('/api/signup', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ name , email, password })
    });

    const result = await response.json();

    if (response.ok && result.ok) {
    alert('สมัครสมาชิกสำเร็จ!');
    location.href = '/home';
    } else {
    alert((result.todo ? "🚧 " : "⚠️ ") + (result.error || 'เกิดข้อผิดพลาดในการสมัครสมาชิก'));
    }
  } catch (error) {
    console.error('Error:', error);
    alert('ไม่สามารถเชื่อมต่อกับเซิร์ฟเวอร์ได้');
  }
});