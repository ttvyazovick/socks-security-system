import React, { ReactElement, useRef } from 'react'
import { useEffect, useState } from 'react'
import ReactDOM from 'react-dom/client'
import './style.css'

import { getStats, loadSocks, toggleCleanStatus, getWashHistory, getSock, addSock, editSock, deleteSock } from './api'

let performSearch = async (_: string) => {}
function Header() {
    const [query, setQuery] = useState<string>('')
    const inputRef = useRef<HTMLInputElement>(null)

    function SearchInput() {
        setQuery(inputRef.current!.value)
        performSearch(inputRef.current!.value)
    }

    return (
        <header>
            <div className="header-top">
                <div className="logo">
                    <i className="fas fa-socks"></i>
                    <h1>Socks Security System</h1>
                </div>
                <div className="header-actions">
                    <a href="/add" className="add-btn">
                        <i className="fas fa-plus"></i> Добавить носок
                    </a>
                    <a href="/about" className="add-btn">
                        <i className="fas fa-info-circle"></i> О системе
                    </a>
                </div>
            </div>
            
            <div className="search-bar">
                <button onClick={SearchInput}>
                    <i className="fas fa-search"></i>
                </button>
                <input type="text" placeholder="Поиск носков по цвету, стилю или бренду..." ref={inputRef} onKeyDown={(e) => { if(e.key == 'Enter') SearchInput() }}/>

                <button id="clearSearch" className="clear-search-btn" style={{display: query === '' ? 'none' : undefined}} onClick={() => { inputRef.current!.value = ''; SearchInput() }}>
                    <i className="fas fa-times"></i> Очистить поиск
                </button>
            </div>
        </header>
    )
}

function StatCard(args: any) {
    return (
        <div className="stat-card">
            <i className={args.iClass}></i>
            <div>
                <h3>{args.stat ?? '0'}</h3>
                <p>{args.text}</p>
            </div>
        </div>
    )
}

let updateStats: () => void = () => {}
function Stats() {
    const [stats, setStats] = useState<any>({})
    updateStats = () => { getStats().then(data => setStats(data.stats)) }
    useEffect(() => { updateStats() }, [])

    return (
        <div className='stats'>
            <StatCard iClass="fas fa-socks" stat={stats.total} text="Всего носков"/>
            <StatCard iClass="fas fa-check-circle" stat={stats.clean} text="Чистые носки"/>
            <StatCard iClass="fas fa-sink" stat={stats.dirty} text="Требуют стирки"/>
            <StatCard iClass="fas fa-shoe-prints" stat={stats.avg_wear_count ? (Math.round(stats.avg_wear_count * 10) / 10).toString() : '0'} text="Средняя носкость"/>
        </div>
    )
}

function PriorityBtn(args: any) {
    return (
        <button
            className={'priority-btn' + (args.priorityState[0] == args.priority ? ' active' : '')}
            onClick={() => args.priorityState[1](args.priority)}>
            {args.text}
            <i className='fas fa-caret-up' style={{marginLeft: '10px'}}></i>
        </button>
    )
}
const isWide = window.innerWidth > 1080

function SockPhoto(args: any) {
    function ZoomPhoto() {
        OpenModal({
            title: args.color + " носки",
            iClass: 'fas fa-socks',
            body: (
                <div className="zoomed-photo">
                    <img src={args.photo_url} alt={args.color + " носки"}></img>
                </div>
            )
        })
    }

    if(args.photo_url) {
        return (
            <img src={args.photo_url} alt={args.color + " носки"} className="sock-photo" loading="lazy" onClick={ZoomPhoto}></img>
        )
    }
    else {
        return (
            <div className="photo-placeholder" style={{backgroundColor: args.color_hex}}>
                <i className="fas fa-socks"></i>
            </div>
        )
    }
}

function DetailItem(args: any) {
    return (
        <span className="detail-item">
            <i className={args.iClass}></i> {args.value}
        </span>
    )
}

function CleanStatus(args: any) {
    if(args.clean) {
        return (
            <div className="clean-status clean">
                <i className="fas fa-check-circle"></i>
                <span>Чистые</span>
            </div>
        )
    }
    else {
        return (
            <div className="clean-status dirty">
                <i className="fas fa-times-circle"></i>
                <span>Грязные</span>
            </div>
        )
    }
}

let OpenModal: (modal: any) => void
function ShowHistory(args: any) {
    async function DisplayHistory() {
        const history = await getWashHistory(args.sockId).then(data => data.history)
        const modal = {
            title: "История стирок",
            iClass: 'fas fa-history',
            body: undefined as ReactElement | undefined
        }
        if(!history || history.length == 0) {
            modal.body = <div className="no-history">
                <i className="fas fa-info-circle"></i>
                <p>История стирок отсутствует</p>
            </div>
        }
        else {
            modal.body = <div className="history-list">
                {history.map((wash_date: any, index: number) => {
                const date = new Date(wash_date).toLocaleDateString('ru-RU', {
                    day: '2-digit',
                    month: '2-digit',
                    year: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
                })
                
                return (
                    <div className="history-item">
                        <div className="history-number">{history.length - index}</div>
                        <div className="history-date">
                            <i className="fas fa-washing-machine"></i>
                            {date}
                        </div>
                    </div>
                )})}
            </div>
        }
        OpenModal(modal)
    }

    return (
        <button className="btn-history" onClick={DisplayHistory}>
            <i className="fas fa-history"></i> История
        </button>
    )
}

function ToggleClean(args: any) {
    const [clean, setClean] = args.cleanState
    async function toggle() {
        const data = await toggleCleanStatus(args.sockId)
        updateStats()
        setClean(!clean)
        args.updateWearCount(args.sockId, data.wear_count)
    }

    if(clean) {
        return (
            <button className="action-btn toggle-clean" onClick={toggle}>
                <i className="fas fa-shoe-prints"></i>
                Испачкать
            </button>
        )
    }
    else {
        return (
            <button className="action-btn toggle-clean" onClick={toggle}>
                <i className="fas fa-sink"></i>
                Постирать
            </button>
        )
    }
}

function DeleteBtn(args: any) {
    async function Delete() {
        await deleteSock(args.sock.id)
        args.unload(args.sock)
        OpenModal(null)
        updateStats()
    }

    function ConfirmDelete() {
        const modal = {
            'title': "Подтверждение удаления",
            'iClass': 'fas fa-exclamation-triangle',
            'body': (
                <div>
                    <p>Вы уверены, что хотите удалить этот носок? Это действие нельзя отменить.</p>
                    <div className="confirm-actions">
                        <button className="btn-cancel" id="cancelDelete" onClick={() => OpenModal(null)}>Отмена</button>
                        <button className="btn-danger" id="confirmDelete" onClick={Delete}>Удалить</button>
                    </div>
                </div>
            )
        }
        OpenModal(modal)
    }

    return (
        <button className="action-btn btn-delete" onClick={ConfirmDelete}>
            <i className="fas fa-trash"></i> Удалить
        </button>
    )
}

function EditBtn(args: any) {
    return (
        <a href={`/edit/${args.sock.id}`} className="action-btn btn-edit">
            <i className="fas fa-pen"></i> Редактировать
        </a>
    )
}

function WideSockRow(args: any) {
    const sock = args.sock
    const cleanState = useState<boolean>(sock.clean)
    useEffect(() => {cleanState[1](sock.clean)}, [sock.clean])
    return (
        <tr>
            <td className="photo-cell">
                <div className="photo-container">
                    <SockPhoto photo_url={sock.photo_url} color={sock.color} color_hex={sock.color_hex}/>
                </div>
            </td>
            <td className="info-cell">
                <div className="sock-info">
                    <h4>{sock.color} носки</h4>
                    <div className="sock-details">
                        <DetailItem iClass="fas fa-tshirt" value={sock.style}/>
                        <DetailItem iClass="fas fa-shapes" value={sock.pattern}/>
                        <DetailItem iClass="fas fa-spa" value={sock.material}/>
                        <DetailItem iClass="fas fa-tag" value={sock.brand}/>
                        <DetailItem iClass="fas fa-ruler" value={sock.size}/>
                    </div>
                    <div className="sock-meta">
                        <small>Добавлено: {sock.created_at_formatted}</small>
                        <small>{sock.last_washed_formatted ? `Стирка: ${sock.last_washed_formatted}` : `` }</small>
                    </div>
                </div>
            </td>
            <td>
                <CleanStatus clean={cleanState[0]}/>
            </td>
            <td className="wear-cell">
                <div className="wear-count">
                    <div className="wear-progress">
                        <div className="wear-bar" style={{width: Math.min(sock.wear_count * 10, 100)}}></div>
                    </div>
                    <span className="wear-number">{sock.wear_count}</span>
                    <small>раз</small>
                </div>
                <ShowHistory sockId={sock.id}/>
            </td>
            <td className="actions-cell">
                <div className="action-buttons">
                    <ToggleClean sockId={sock.id} cleanState={cleanState} updateWearCount={args.updateWearCount}/>
                    <EditBtn sock={sock}/>
                    <DeleteBtn sock={sock} unload={args.unload}/>
                </div>
            </td>
        </tr>
    )
}

function ThinSockRow(args: any) {
    const sock = args.sock
    const cleanState = useState<boolean>(sock.clean)
    useEffect(() => {cleanState[1](sock.clean)}, [sock.clean])
    return (
        <div className="sock-row">
            <div className="photo-cell">
                <div className="photo-container">
                    <SockPhoto photo_url={sock.photo_url} color={sock.color} color_hex={sock.color}/>
                </div>
            </div>
            <div className="info-cell">
                <div className="sock-info">
                    <div className="main-sock-info">
                        <h4>{sock.color} носки</h4>
                        <CleanStatus clean={cleanState[0]}/>
                    </div>
                    <div className="sock-details">
                        <DetailItem iClass="fas fa-tshirt" value={sock.style}/>
                        <DetailItem iClass="fas fa-shapes" value={sock.pattern}/>
                        <DetailItem iClass="fas fa-spa" value={sock.material}/>
                        <DetailItem iClass="fas fa-tag" value={sock.brand}/>
                        <DetailItem iClass="fas fa-ruler" value={sock.size}/>
                    </div>
                    <div className="sock-meta">
                        <small>Добавлено: {sock.created_at_formatted}</small>
                        <small>{sock.last_washed_formatted ? `Стирка: ${sock.last_washed_formatted}` : `` }</small>
                    </div>
                </div>
            </div>
            <div className="wear-cell">
                <div className="wear-count">
                    <div className="wear-progress">
                        <div className="wear-bar" style={{width: Math.min(sock.wear_count * 10, 100)}}></div>
                    </div>
                    <span className="wear-number">{sock.wear_count}</span>
                    <small>раз</small>
                    <button className="btn-history">
                        <i className="fas fa-history"></i> История
                    </button>
                </div>
            </div>
            <div className="actions-cell">
                <div className="action-buttons">
                    <ToggleClean sockId={sock.id} cleanState={cleanState} updateWearCount={args.updateWearCount}/>
                    <EditBtn sock={sock}/>
                    <DeleteBtn sock={sock} unload={args.unload}/>
                </div>
            </div>
        </div>
    )
}

function SocksTable(args: any) {
    if(isWide) {
        return (
            <table>
                <thead>
                    <tr>
                        <th>Фото</th>
                        <th>Информация</th>
                        <th>Статус</th>
                        <th>Носкость</th>
                        <th>Действия</th>
                    </tr>
                </thead>
                <tbody>{args.socks.map((sock: any) => <WideSockRow sock={sock} unload={args.unload} updateWearCount={args.updateWearCount}/>)}</tbody>
            </table>
        )
    }
    else {
        return (
            <div>{args.socks.map((sock: any) => <ThinSockRow sock={sock} unload={args.unload} updateWearCount={args.updateWearCount}/>)}</div>
        )
    }
}

function LoadMorebtn(args: any) {
    return (
        <div className="table-end">
            <button onClick={args.loadMoreSocks}>
                <i className="fas fa-plus"></i>
                Загрузить еще...
            </button>
        </div>
    )
}

function Content() {
    const priorityState = useState<string>('clean')
    const [socks, setSocks] = useState<any[]>([])

    let query = ''
    performSearch = async (newQuery: string) => {
        query = newQuery
        loadMoreSocks(true)
    }

    async function loadMoreSocks(reload = false, load = 5) {
        const newSocks = await loadSocks(query, reload ? 0 : socks.length, load, priorityState[0])
        if(newSocks)
            setSocks(prev => reload ? newSocks : prev.concat(newSocks))
    }
    function unload(sock: any) {
        setSocks(prev => [...prev.slice(0, prev.indexOf(sock)), ...prev.slice(prev.indexOf(sock) + 1, prev.length)])
    }
    function updateWearCount(sockId: string, wearCount: number) {
        setSocks(prev => prev.map(sock => sock.id == sockId ? {...sock, wear_count: wearCount} : sock))
    }
    useEffect(() => { loadMoreSocks(true) }, [priorityState[0]])

    return (
        <main>
            <div className="table-header">
                <h2><i className="fas fa-list"></i> Коллекция носков</h2>
                <div>
                    <PriorityBtn priorityState={priorityState} priority="clean" text="Чистые"/>
                    <PriorityBtn priorityState={priorityState} priority="dirty" text="Грязные"/>
                    <PriorityBtn priorityState={priorityState} priority="frequent" text="Часто носимые"/>
                </div>
            </div>

            <SocksTable priority={priorityState[0]} socks={socks} unload={unload} updateWearCount={updateWearCount}/>
            <LoadMorebtn loadMoreSocks={() => loadMoreSocks()}/>
        </main>
    )
}

function Footer() {
    return (
        <footer className="footer">
            <p>© 2026 Socks Security System. Все права защищены.</p>
        </footer>
    )
}

function Modal(args: any) {
    const modal = args.modal
    if(modal === null)
        return ( <div></div> )
    return (
        <div className="modal">
            <div className="modal-content">
                <div className="modal-header">
                    <h2><i className={modal.iClass}></i>{ modal.title }</h2>
                    <button className="close-modal" onClick={() => OpenModal(null)}>&times;</button>
                </div>
                <div className="modal-body">
                    { modal.body }
                </div>
            </div>
        </div>
    )
}

function MainPage(args: any) {
    return (
        <div>
            <div className="container">
                <Header/>
                <Stats/>
                <Content/>
                <Footer/>
            </div>
            <Modal modal={args.modal}/>
        </div>
    )
}

function ColorOption(args: any) {
    const color = args.color
    return (
        <button type="button" className={'color-option' + (args.colorState[0]?.hex == color.hex ? ' selected' : '')} style={{backgroundColor: color.hex }} onClick={() => args.colorState[1](color)}>
            <i className="fas fa-check"></i>
        </button>
    )
}

function ColorInput(args: any) {
    const color_options = [
        {'name': 'Черные', 'hex': '#2c3e50'},
        {'name': 'Белые', 'hex': '#ecf0f1'},
        {'name': 'Серые', 'hex': '#7f8c8d'},
        {'name': 'Синие', 'hex': '#3498db'},
        {'name': 'Зеленые', 'hex': '#27ae60'},
        {'name': 'Красные', 'hex': '#e74c3c'},
        {'name': 'Желтые', 'hex': '#f1c40f'},
        {'name': 'Фиолетовые', 'hex': '#9b59b6'},
        {'name': 'Розовые', 'hex': '#e84393'},
        {'name': 'Оранжевые', 'hex': '#e67e22'},
        {'name': 'Голубые', 'hex': '#00cec9'},
        {'name': 'Коричневые', 'hex': '#a1887f'},
        {'name': 'Бежевые', 'hex': '#f5deb3'},
        {'name': 'Бирюзовые', 'hex': '#1abc9c'},
        {'name': 'Мятные', 'hex': '#98ff98'},
    ]
    const colorState = useState<any>(args.value ?? {})
    const curColor = colorState[0]

    return (
        <div className="form-group">
            <label htmlFor="color">
                <i className="fas fa-fill-drip"></i> Цвет
            </label>
            <div className="color-selector">
                {color_options.map(color => <ColorOption color={color} colorState={colorState}/>
                )}
            </div>
            <input type="hidden" name="color" value={curColor.name} required/>
            <input type="hidden" name="color_hex" value={curColor.hex}/>
            <div className="selected-color-display">
                <span>{curColor.name ?? "Выберите цвет"}</span>
                <div id="selectedColorPreview" style={{
                    display: curColor === null ? 'none' : undefined, backgroundColor: curColor.hex ?? undefined
                }}></div>
            </div>
        </div>
    )
}

function ParamInput(args: any) {
    return (
        <div className="form-group">
            <label htmlFor="style">
                <i className={args.iClass}></i>{args.title}
            </label>
            <select name={args.name} defaultValue={args.value ?? ''} required>
                <option value="">{args.hint}</option>
                {args.options.map((opt: any) => <option value={opt}>{opt}</option>)}
            </select>
        </div>
    )
}

function ImagePreview(args: any) {
    if(args.src) {
        return (
            <div className="file-preview">
                <div className="preview-image">
                    <img src={args.src} alt="Не удалось отобразить ваше фото"/>
                    <div className="preview-overlay">
                        <button type="button" className="btn-remove-preview" onClick={args.remove}>
                            <i className="fas fa-times"></i> Удалить
                        </button>
                    </div>
                </div>
            </div>
        )
    }
    else {
        return (
            <div className="file-preview">
                <div className="preview-placeholder">
                    <i className="fas fa-cloud-upload-alt"></i>
                    <p>Выберите файл для предпросмотра</p>
                </div>
            </div>
        )
    }
}

function ImageInput(args: any) {
    const [src, setSrc] = useState<string>(args.src ?? '')
    const fileRef = useRef(null as HTMLInputElement | null)
    return (
        <div className="form-group">
            <label htmlFor="photo">
                <i className="fas fa-camera"></i> Фотография носка
            </label>
            <input type="file" name="photo" accept="image/*" className="file-input" ref={fileRef} onChange={(e) => setSrc(e.target.files?.length ? URL.createObjectURL(e.target.files[0]) : '')}/>
            <small className="form-hint">Можно загрузить фото с компьютера (PNG, JPG, WEBP, до 16MB)</small>
            <ImagePreview src={src} remove={() => { fileRef.current!.value = ''; setSrc(args.src ?? '') }}/>
        </div>
    )
}

function AddSockPage(args: any) {
    const isEdit = args.sockId !== undefined
    const [sock, setSock] = useState<any>(null)

    let style_options = [
        'Спортивные', 'Повседневные', 'Домашние', 
        'Бизнес', 'Короткие', 'Термо', 'Вязаные',
        'Смешные', 'Праздничные'
    ]
    let pattern_options = [
        'Однотонные', 'Полоска', 'Горошек', 'Клетка',
        'Геометрия', 'Принт', 'Логотип'
    ]
    let material_options = ['Хлопок', 'Шерсть', 'Синтетика', 'Шелк', 'Бамбук', 'Лен',]
    let size_options = ['XS', 'S', 'M', 'L', 'XL', 'XXL', 'XXXL']
    let brand_options = ['Nike', 'Puma', 'Reebok', 'Uniqlo', 'H&M', 'Wilson', 'Funny Socks', 'Unknown']

    useEffect(() => {
        if(isEdit) {
            getSock(args.sockId).then(data => setSock(data))
        }
    }, [])

    async function Submit(e: any) {
        e.preventDefault()
        const data = new FormData(e.target)
        if(isEdit) {
            await editSock(args.sockId, data)
        }
        else {
            await addSock(data)
        }
        const modal = {
            title: isEdit ? 'Носок обновлен' : 'Носок добавлен',
            iClass: 'fas fa-check-circle',
            body: (
                <div className='success-modal'>
                    <a href='/' className='btn-primary' style={{textDecoration: 'none'}}>На главную страницу</a>
                    {!isEdit && <button onClick={() => OpenModal(null)} className='btn-secondary'>Добавить еще</button>}
                </div>
            )
        }
        OpenModal(modal)
    }

    if(isEdit && sock === null) {
        return (
            <div>
                <div className="container">
                    <header>
                        <div className="logo">
                            <i className="fas fa-socks"></i>
                            <h1>Редактировать носок</h1>
                        </div>
                    </header>
                    <main>
                        <p>Загрузка...</p>
                    </main>
                </div>
                <Footer/>
            </div>
        )
    }

    return (
        <div>
            <div className="container">
                <header>
                    <div className="logo">
                        <i className="fas fa-socks"></i>
                        <h1>{isEdit ? 'Редактировать носок' : 'Добавить носок'}</h1>
                    </div>
                    <p className="subtitle">{isEdit ? 'Обновите информацию о носке' : 'Добавьте новый носок в вашу коллекцию'}</p>
                </header>

                <nav className="breadcrumb">
                    <a href="/"><i className="fas fa-home"></i> Главная</a>
                    <i className="fas fa-chevron-right"></i>
                    <span>{isEdit ? 'Редактировать носок' : 'Добавить носок'}</span>
                </nav>

                <main>
                    <form id="addSockForm" className="sock-form" onSubmit={(e) => Submit(e)}>
                        <div className="form-section">
                            <ColorInput value={sock ? {'name': sock.color, 'hex': sock.color_hex} : undefined}/>
                            <ParamInput iClass="fas fa-socks" title="Стиль" hint="Выберите стиль" name="style" options={style_options} value={sock?.style}/>
                            <ParamInput iClass="fas fa-shapes" title="Узор" hint="Выберите узор" name="pattern" options={pattern_options} value={sock?.pattern}/>
                            <ParamInput iClass="fas fa-spa" title="Материал" hint="Выберите материал" name="material" options={material_options} value={sock?.material}/>
                            <ParamInput iClass="fas fa-ruler" title="Размер" hint="Выберите размер" name="size" options={size_options} value={sock?.size}/>
                            <ParamInput iClass="fas fa-tag" title="Бренд" hint="Выберите бренд" name="brand" options={brand_options} value={sock?.brand}/>
                            <ImageInput src={sock?.photo_url}/>
                        </div>

                        <div className="form-actions">
                            <button type="button" className="btn-secondary" onClick={() => window.location.href='/'}>
                                <i className="fas fa-times"></i> Отмена
                            </button>
                            <button type="submit" className="btn-primary">
                                <i className={isEdit ? 'fas fa-save' : 'fas fa-plus'}></i> {isEdit ? 'Сохранить' : 'Добавить носок'}
                            </button>
                        </div>
                    </form>
                </main>
                <Modal modal={args.modal}/>
            </div>
            <Footer/>
        </div>
    )
}

function About() {
    return (
        <div>
            <div className="container">
                <header>
                    <div className="logo">
                        <i className="fas fa-socks"></i>
                        <h1>О системе</h1>
                    </div>
                </header>
                <nav className="breadcrumb">
                    <a href="/"><i className="fas fa-home"></i> Главная</a>
                    <i className="fas fa-chevron-right"></i>
                    <span>О системе</span>
                </nav>
                <main>
                    <h2>О Socks Security System</h2>
                    <p>Socks Security System - это приложение для управления вашей коллекцией носков. Оно помогает отслеживать состояние носков, их носкость и историю стирок.</p>
                </main>
            </div>
            <Footer/>
        </div>
    )
}

function App() {
    const [modalLink, setModal] = useState<any>(null)
    OpenModal = (modal: any) => {
        setModal(modal)
    }
    switch(window.location.href.split('/')[3]) {
    case 'add':
        return <AddSockPage modal={modalLink}/>
    case 'edit':
        return <AddSockPage modal={modalLink} sockId={window.location.href.split('/')[4]}/>
    case 'about':
        return <About/>
    default:
        return <MainPage modal={modalLink}/>
    }
}

const root = ReactDOM.createRoot(
    document.getElementById('root') as HTMLElement
)
root.render(<App/>)
