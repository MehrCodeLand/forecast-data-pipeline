// Bilingual UI strings. Default language is Farsi; the user can switch
// with the toggle in the navbar and the choice persists in localStorage.

const I18N = {
    en: {
        nav_home: 'Home',
        nav_cities: 'Cities',
        nav_info: 'Info',
        nav_compare: 'Compare',
        coming_soon: 'Buy me a coffee - coming soon!',
        map_title: 'Live Map',
        map_note: 'Every dot is a tracked city. Hover for the latest conditions; click to open its dashboard.',
        compare_title: 'Compare Cities',
        compare_pick: 'Pick 2 to 4 cities and see their temperature and wind side by side.',
        compare_btn: 'Compare',
        compare_table_title: 'Side by Side',
        compare_need_more: 'At least two cities are needed for a comparison.',
        metric: 'Metric',
        theme_toggle: 'Toggle light/dark theme',
        default_tagline: 'Weather data collection and analysis, city by city',
        default_intro: 'We continuously collect current weather conditions for cities around the world and turn them into clear, comparable analytics. Pick a city to explore its temperature and wind behaviour over time.',
        default_examples: 'For every city we track average temperature, temperature range and rate of change, wind speed and direction, calm periods, and more - all computed from data we collect ourselves at regular intervals.',
        default_about_title: 'About This Project',
        default_about: 'This project is an independent weather data pipeline. We fetch current conditions for each tracked city on a fixed schedule, store every snapshot, and compute analytics over the collected history.',
        default_mission: 'Our goal is to make raw weather history accessible and understandable. All figures on this site come from our own collected snapshots.',
        default_data_desc: 'For each city we store the current temperature, wind speed, wind direction, day/night flag and weather code, together with a timestamp.',
        default_footer: 'Weather Analysis System',
        explore_cities: 'Explore Cities',
        about_project: 'About the Project',
        cities_we_track: 'Cities We Track',
        see_all: 'See all',
        what_you_find: 'What You Will Find Here',
        temp_analytics: 'Temperature Analytics',
        temp_analytics_desc: 'Average temperature, minimum and maximum range, rate of change and hourly delta, computed over the most recent records of each city.',
        wind_analytics: 'Wind Analytics',
        wind_analytics_desc: 'Average and peak wind speed, dominant direction, direction variability and calm-period detection with a configurable threshold.',
        raw_history: 'Raw History',
        raw_history_desc: 'Every snapshot we collect is stored and browsable, so you can see exactly how conditions evolved over time.',
        how_it_works: 'How It Works',
        loading: 'Loading...',
        error_cities: 'Could not load cities. Please check if the API is running.',
        error_city: 'Could not load this city. It may not exist, or the API is not running.',
        error_content: 'Could not load site content. Please check if the API is running.',
        no_cities: 'No cities are being tracked yet.',
        no_data_yet: 'No data yet',
        latest_temperature: 'latest temperature',
        wind_label: 'Wind:',
        records_label: 'Records collected:',
        last_update: 'Last update:',
        cities_title: 'Cities',
        pick_city: 'Pick a city to open its dashboard with temperature, wind and raw data analytics.',
        summary: 'Summary',
        temperature: 'Temperature',
        wind: 'Wind',
        recent_data: 'Recent Data',
        period_label: 'Period (records):',
        refresh: 'Refresh',
        average: 'Average',
        range: 'Range',
        rate_of_change: 'Rate of Change',
        delta_per_hour: 'Delta per Hour',
        avg_speed: 'Average Speed',
        peak_speed: 'Peak Speed',
        dominant_direction: 'Dominant Direction',
        direction_variability: 'Direction Variability',
        calm_periods: 'Calm Periods',
        threshold_label: 'Threshold (km/h):',
        calculate: 'Calculate',
        calm_count_label: 'Calm periods:',
        total_periods_label: 'Total periods:',
        calm_pct_label: 'Calm percentage:',
        rows_label: 'Rows:',
        load: 'Load',
        total_records_label: 'Total records:',
        showing_label: 'Showing:',
        th_id: 'ID',
        th_time: 'Time',
        th_temp: 'Temperature (C)',
        th_wind: 'Wind (km/h)',
        th_dir: 'Direction',
        th_code: 'Code',
        th_daynight: 'Day/Night',
        day: 'Day',
        night: 'Night',
        min_label: 'Min:',
        max_label: 'Max:',
        range_label: 'Range:',
        peak_label: 'Peak:',
        deg_c: 'degrees C',
        deg_c_avg: 'degrees C average',
        deg_c_per_hour: 'degrees C / hour',
        kmh: 'km/h',
        kmh_avg: 'km/h average',
        degrees: 'degrees',
        std_dev: 'std deviation',
        pct_calm: '% calm time',
        analyzed: 'analyzed',
        data_points: 'Data Points',
        wind_speed: 'Wind Speed',
        wind_direction: 'Wind Direction',
        records_collected: 'records collected',
        who_we_are: 'Who We Are',
        our_mission: 'Our Mission',
        data_we_collect: 'The Data We Collect',
        contact: 'Contact',
        contact_line: 'Questions or suggestions? Reach us at',
        developers: 'Developers',
        dev_mehrshad: 'Mehrshad Asadi',
        dev_sepehr: 'Sepehr Sedigh',
        linkedin: 'LinkedIn',
        trends: 'Trends',
        temp_trend: 'Temperature over time',
        wind_trend: 'Wind speed over time',
        chart_empty: 'Not enough data to chart yet.',
        records_milestones: 'Records & Milestones',
        records_note: "All-time highlights computed over this city's full collected history.",
        hottest: 'Hottest',
        coldest: 'Coldest',
        windiest: 'Windiest',
        longest_calm: 'Longest Calm Streak',
        consecutive_records: 'consecutive records',
        wettest: 'Wettest',
        most_humid: 'Most Humid',
        feels_like: 'Feels Like',
        humidity: 'Humidity',
        precipitation: 'Precipitation',
        pressure: 'Pressure',
        pct: '% average',
        mm_total: 'mm total',
        hpa: 'hPa average',
    },
    fa: {
        nav_home: 'خانه',
        nav_cities: 'شهرها',
        nav_info: 'درباره',
        nav_compare: 'مقایسه',
        coming_soon: 'یک قهوه مهمانم کن - به‌زودی!',
        map_title: 'نقشه زنده',
        map_note: 'هر نقطه یک شهر رصدشده است. برای دیدن آخرین وضعیت، نشانگر را روی آن ببرید و برای باز کردن داشبورد کلیک کنید.',
        compare_title: 'مقایسه شهرها',
        compare_pick: 'دو تا چهار شهر را انتخاب کنید و دما و باد آن‌ها را کنار هم ببینید.',
        compare_btn: 'مقایسه',
        compare_table_title: 'کنار هم',
        compare_need_more: 'برای مقایسه دست‌کم دو شهر لازم است.',
        metric: 'شاخص',
        theme_toggle: 'تغییر حالت روشن/تاریک',
        default_tagline: 'جمع‌آوری و تحلیل داده‌های هواشناسی، شهر به شهر',
        default_intro: 'ما به‌طور پیوسته وضعیت آب‌وهوای شهرهای مختلف جهان را جمع‌آوری می‌کنیم و آن را به تحلیل‌های روشن و قابل مقایسه تبدیل می‌کنیم. یک شهر را انتخاب کنید تا رفتار دما و باد آن را در طول زمان ببینید.',
        default_examples: 'برای هر شهر میانگین دما، بازه دما و نرخ تغییر، سرعت و جهت باد، دوره‌های آرام و موارد دیگر را دنبال می‌کنیم - همه از داده‌هایی که خودمان در بازه‌های منظم جمع‌آوری می‌کنیم.',
        default_about_title: 'درباره این پروژه',
        default_about: 'این پروژه یک سامانه مستقل جمع‌آوری داده‌های هواشناسی است. ما وضعیت لحظه‌ای هر شهر را طبق برنامه زمان‌بندی دریافت می‌کنیم، هر رکورد را ذخیره می‌کنیم و روی تاریخچه جمع‌آوری‌شده تحلیل انجام می‌دهیم.',
        default_mission: 'هدف ما دسترس‌پذیر و قابل فهم کردن تاریخچه خام آب‌وهواست. همه اعداد این سایت از رکوردهایی که خودمان جمع کرده‌ایم به دست می‌آید.',
        default_data_desc: 'برای هر شهر دمای فعلی، سرعت باد، جهت باد، شاخص روز/شب و کد وضعیت هوا را همراه با برچسب زمانی ذخیره می‌کنیم.',
        default_footer: 'سامانه تحلیل آب‌وهوا',
        explore_cities: 'مشاهده شهرها',
        about_project: 'درباره پروژه',
        cities_we_track: 'شهرهایی که رصد می‌کنیم',
        see_all: 'مشاهده همه',
        what_you_find: 'اینجا چه چیزهایی خواهید یافت',
        temp_analytics: 'تحلیل دما',
        temp_analytics_desc: 'میانگین دما، کمینه و بیشینه، نرخ تغییر و دلتای ساعتی، محاسبه‌شده روی جدیدترین رکوردهای هر شهر.',
        wind_analytics: 'تحلیل باد',
        wind_analytics_desc: 'سرعت میانگین و بیشینه باد، جهت غالب، تغییرپذیری جهت و تشخیص دوره‌های آرام با آستانه قابل تنظیم.',
        raw_history: 'تاریخچه خام',
        raw_history_desc: 'هر رکوردی که جمع‌آوری می‌کنیم ذخیره و قابل مشاهده است تا دقیقاً ببینید شرایط در طول زمان چگونه تغییر کرده است.',
        how_it_works: 'چگونه کار می‌کند',
        loading: 'در حال بارگذاری...',
        error_cities: 'بارگذاری شهرها ممکن نشد. لطفاً از در دسترس بودن سرویس مطمئن شوید.',
        error_city: 'بارگذاری این شهر ممکن نشد. ممکن است وجود نداشته باشد یا سرویس در دسترس نباشد.',
        error_content: 'بارگذاری محتوای سایت ممکن نشد. لطفاً از در دسترس بودن سرویس مطمئن شوید.',
        no_cities: 'هنوز شهری رصد نمی‌شود.',
        no_data_yet: 'هنوز داده‌ای نیست',
        latest_temperature: 'آخرین دما',
        wind_label: 'باد:',
        records_label: 'رکوردهای جمع‌آوری‌شده:',
        last_update: 'آخرین به‌روزرسانی:',
        cities_title: 'شهرها',
        pick_city: 'یک شهر را انتخاب کنید تا داشبورد دما، باد و داده‌های خام آن را ببینید.',
        summary: 'خلاصه',
        temperature: 'دما',
        wind: 'باد',
        recent_data: 'داده‌های اخیر',
        period_label: 'بازه (تعداد رکورد):',
        refresh: 'به‌روزرسانی',
        average: 'میانگین',
        range: 'بازه تغییرات',
        rate_of_change: 'نرخ تغییر',
        delta_per_hour: 'دلتا در ساعت',
        avg_speed: 'سرعت میانگین',
        peak_speed: 'سرعت بیشینه',
        dominant_direction: 'جهت غالب',
        direction_variability: 'تغییرپذیری جهت',
        calm_periods: 'دوره‌های آرام',
        threshold_label: 'آستانه (کیلومتر بر ساعت):',
        calculate: 'محاسبه',
        calm_count_label: 'دوره‌های آرام:',
        total_periods_label: 'کل دوره‌ها:',
        calm_pct_label: 'درصد آرام:',
        rows_label: 'تعداد ردیف:',
        load: 'بارگذاری',
        total_records_label: 'کل رکوردها:',
        showing_label: 'نمایش:',
        th_id: 'شناسه',
        th_time: 'زمان',
        th_temp: 'دما (سانتی‌گراد)',
        th_wind: 'باد (km/h)',
        th_dir: 'جهت',
        th_code: 'کد',
        th_daynight: 'روز/شب',
        day: 'روز',
        night: 'شب',
        min_label: 'کمینه:',
        max_label: 'بیشینه:',
        range_label: 'بازه:',
        peak_label: 'بیشینه:',
        deg_c: 'درجه سانتی‌گراد',
        deg_c_avg: 'میانگین، درجه سانتی‌گراد',
        deg_c_per_hour: 'درجه سانتی‌گراد در ساعت',
        kmh: 'کیلومتر بر ساعت',
        kmh_avg: 'میانگین، کیلومتر بر ساعت',
        degrees: 'درجه',
        std_dev: 'انحراف معیار',
        pct_calm: 'درصد زمان آرام',
        analyzed: 'تحلیل‌شده',
        data_points: 'تعداد داده',
        wind_speed: 'سرعت باد',
        wind_direction: 'جهت باد',
        records_collected: 'رکورد جمع‌آوری‌شده',
        who_we_are: 'ما که هستیم',
        our_mission: 'ماموریت ما',
        data_we_collect: 'داده‌هایی که جمع می‌کنیم',
        contact: 'تماس',
        contact_line: 'پرسش یا پیشنهادی دارید؟ با ما در تماس باشید:',
        developers: 'توسعه‌دهندگان',
        dev_mehrshad: 'مهرشاد اسدی',
        dev_sepehr: 'سپهر صدیق',
        linkedin: 'لینکدین',
        trends: 'روند تغییرات',
        temp_trend: 'دما در طول زمان',
        wind_trend: 'سرعت باد در طول زمان',
        chart_empty: 'هنوز داده کافی برای رسم نمودار وجود ندارد.',
        records_milestones: 'رکوردها و نقاط عطف',
        records_note: 'برجسته‌ترین رکوردها که روی کل تاریخچه جمع‌آوری‌شده این شهر محاسبه شده است.',
        hottest: 'گرم‌ترین',
        coldest: 'سردترین',
        windiest: 'بادخیزترین',
        longest_calm: 'طولانی‌ترین دوره آرام',
        consecutive_records: 'رکورد متوالی',
        wettest: 'پربارش‌ترین',
        most_humid: 'مرطوب‌ترین',
        feels_like: 'دمای محسوس',
        humidity: 'رطوبت',
        precipitation: 'بارش',
        pressure: 'فشار هوا',
        pct: 'میانگین (درصد)',
        mm_total: 'مجموع (میلی‌متر)',
        hpa: 'میانگین (هکتوپاسکال)',
    }
};

const CURRENT_LANG = (() => {
    const saved = localStorage.getItem('lang');
    return (saved === 'en' || saved === 'fa') ? saved : 'fa';
})();

function t(key) {
    return (I18N[CURRENT_LANG] && I18N[CURRENT_LANG][key]) || I18N.en[key] || key;
}

function applyLanguage() {
    document.documentElement.lang = CURRENT_LANG;
    document.documentElement.dir = CURRENT_LANG === 'fa' ? 'rtl' : 'ltr';

    document.querySelectorAll('[data-i18n]').forEach(el => {
        el.textContent = t(el.dataset.i18n);
    });

    const toggle = document.getElementById('lang-toggle');
    if (toggle) {
        // The button shows the language you would switch TO
        toggle.textContent = CURRENT_LANG === 'fa' ? 'EN' : 'فارسی';
        toggle.addEventListener('click', () => {
            localStorage.setItem('lang', CURRENT_LANG === 'fa' ? 'en' : 'fa');
            window.location.reload();
        });
    }
}

// ---- Theme (light/dark). Default follows the system preference; the
// navbar toggle overrides it and the choice persists. ----

const THEME_ICONS = {
    // shown on the button is the theme you would switch TO
    sun: '<svg viewBox="0 0 16 16" width="15" height="15" fill="currentColor" aria-hidden="true"><path d="M8 12a4 4 0 1 1 0-8 4 4 0 0 1 0 8Zm0-1.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5ZM8 0a.75.75 0 0 1 .75.75v1a.75.75 0 0 1-1.5 0v-1A.75.75 0 0 1 8 0Zm0 13.5a.75.75 0 0 1 .75.75v1a.75.75 0 0 1-1.5 0v-1A.75.75 0 0 1 8 13.5ZM2.343 2.343a.75.75 0 0 1 1.061 0l.708.707a.75.75 0 0 1-1.061 1.061l-.708-.707a.75.75 0 0 1 0-1.061Zm9.545 9.545a.75.75 0 0 1 1.06 0l.708.708a.75.75 0 1 1-1.06 1.06l-.708-.707a.75.75 0 0 1 0-1.06ZM0 8a.75.75 0 0 1 .75-.75h1a.75.75 0 0 1 0 1.5h-1A.75.75 0 0 1 0 8Zm13.5 0a.75.75 0 0 1 .75-.75h1a.75.75 0 0 1 0 1.5h-1A.75.75 0 0 1 13.5 8ZM4.112 11.888a.75.75 0 0 1 0 1.06l-.708.708a.75.75 0 1 1-1.06-1.06l.707-.708a.75.75 0 0 1 1.06 0Zm9.545-9.545a.75.75 0 0 1 0 1.061l-.707.707a.75.75 0 1 1-1.061-1.06l.707-.708a.75.75 0 0 1 1.061 0Z"/></svg>',
    moon: '<svg viewBox="0 0 16 16" width="15" height="15" fill="currentColor" aria-hidden="true"><path d="M9.598 1.591a.749.749 0 0 1 .785-.175 7.001 7.001 0 1 1-8.967 8.967.75.75 0 0 1 .961-.96 5.5 5.5 0 0 0 7.046-7.046.75.75 0 0 1 .175-.786Zm1.616 1.945a7 7 0 0 1-7.678 7.678 5.499 5.499 0 1 0 7.678-7.678Z"/></svg>'
};

const CURRENT_THEME = (() => {
    const saved = localStorage.getItem('theme');
    if (saved === 'light' || saved === 'dark') return saved;
    return (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches)
        ? 'light' : 'dark';
})();

function applyTheme() {
    document.documentElement.dataset.theme = CURRENT_THEME;

    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.content = CURRENT_THEME === 'light' ? '#f6f8fa' : '#0d1117';

    const toggle = document.getElementById('theme-toggle');
    if (toggle) {
        toggle.innerHTML = CURRENT_THEME === 'light' ? THEME_ICONS.moon : THEME_ICONS.sun;
        toggle.setAttribute('aria-label', t('theme_toggle'));
        toggle.setAttribute('title', t('theme_toggle'));
        toggle.addEventListener('click', () => {
            localStorage.setItem('theme', CURRENT_THEME === 'light' ? 'dark' : 'light');
            window.location.reload();
        });
    }
}

applyLanguage();
applyTheme();
