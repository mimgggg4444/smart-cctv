// 스크롤 진행 바
window.addEventListener('scroll', () => {
    const scrollProgress = document.getElementById('scroll-progress');
    const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
    const scrollHeight = document.documentElement.scrollHeight - document.documentElement.clientHeight;
    const scrollPercentage = (scrollTop / scrollHeight) * 100;
    scrollProgress.style.width = scrollPercentage + '%';
});

// 언어 전환 함수
let currentLang = localStorage.getItem('language') || 'ko';

function switchLanguage(lang) {
    currentLang = lang;
    localStorage.setItem('language', lang);

    // 버튼 활성화 상태 변경
    document.getElementById('lang-ko').classList.toggle('active', lang === 'ko');
    document.getElementById('lang-en').classList.toggle('active', lang === 'en');
    document.getElementById('lang-zh').classList.toggle('active', lang === 'zh');

    // HTML lang 속성 변경
    document.documentElement.lang = lang === 'zh' ? 'zh-CN' : lang;

    // 모든 data-ko, data-en, data-zh 속성을 가진 요소 찾기
    document.querySelectorAll('[data-ko][data-en]').forEach(element => {
        const text = element.getAttribute(`data-${lang}`);
        if (text) {
            if (element.tagName === 'INPUT' || element.tagName === 'TEXTAREA') {
                if (element.hasAttribute(`data-${lang}-placeholder`)) {
                    element.placeholder = element.getAttribute(`data-${lang}-placeholder`);
                }
            } else if (element.tagName === 'OPTION') {
                element.textContent = text;
            } else {
                element.innerHTML = text;
            }
        }
    });
}

// 페이지 로드 시 저장된 언어 적용
window.addEventListener('DOMContentLoaded', () => {
    switchLanguage(currentLang);
});

// 부드러운 스크롤
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

// 폼 제출 처리
function handleSubmit(event) {
    event.preventDefault();

    const formData = new FormData(event.target);
    const data = Object.fromEntries(formData);

    console.log('신청 데이터:', data);

    const message = currentLang === 'ko'
        ? '베타 테스터 신청이 완료되었습니다!\n빠른 시일 내에 연락드리겠습니다.'
        : currentLang === 'zh'
        ? 'Beta测试申请已完成！\n我们将尽快与您联系。'
        : 'Beta testing application completed!\nWe will contact you soon.';

    alert(message);
    event.target.reset();

    // 실제로는 여기서 서버로 데이터 전송
    // fetch('/api/beta-signup', {
    //     method: 'POST',
    //     headers: { 'Content-Type': 'application/json' },
    //     body: JSON.stringify(data)
    // })
}

// 스크롤 애니메이션
const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -100px 0px'
};

const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.style.opacity = '1';
            entry.target.style.transform = 'translateY(0)';
        }
    });
}, observerOptions);

// 애니메이션 적용할 요소들
document.addEventListener('DOMContentLoaded', () => {
    const animateElements = document.querySelectorAll('.tech-item, .ai-card, .solution-card, .spec-row');
    animateElements.forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(30px)';
        el.style.transition = 'opacity 0.6s cubic-bezier(0.4, 0, 0.2, 1), transform 0.6s cubic-bezier(0.4, 0, 0.2, 1)';
        observer.observe(el);
    });
});
