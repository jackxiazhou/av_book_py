import React, { useState, useEffect } from 'react';
import './App.css';

function App() {
  // 状态管理
  const [currentView, setCurrentView] = useState('actresses'); // actresses, actress-detail, movies, movie-detail, stats
  const [actresses, setActresses] = useState([]);
  const [movies, setMovies] = useState([]);
  const [selectedActress, setSelectedActress] = useState(null);
  const [selectedMovie, setSelectedMovie] = useState(null);
  const [actressMovies, setActressMovies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [stats, setStats] = useState(null);

  // 筛选状态
  const [actressFilters, setActressFilters] = useState({
    search: '',
    cupSize: '',
    heightRange: '',
    hasPhotos: '',
    sortBy: 'name'
  });

  const [movieFilters, setMovieFilters] = useState({
    search: '',
    studio: '',
    year: '',
    duration: '',
    sortBy: 'release_date'
  });

  useEffect(() => {
    fetchInitialData();
  }, []);

  // 获取初始数据
  const fetchInitialData = async () => {
    try {
      setLoading(true);
      await Promise.all([
        fetchActresses(),
        fetchMovies(),
        fetchStats()
      ]);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // 获取女友列表
  const fetchActresses = async (filterParams = {}) => {
    try {
      const currentFilters = { ...actressFilters, ...filterParams };
      const params = new URLSearchParams({
        page_size: 50,
        ordering: currentFilters.sortBy,
      });

      if (currentFilters.search) {
        params.append('search', currentFilters.search);
      }

      if (currentFilters.cupSize) {
        params.append('cup_size', currentFilters.cupSize);
      }

      if (currentFilters.heightRange) {
        params.append('heightRange', currentFilters.heightRange);
      }

      if (currentFilters.hasPhotos) {
        params.append('hasPhotos', currentFilters.hasPhotos);
      }

      const response = await fetch(`http://localhost:8000/api/actresses/?${params}`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      setActresses(data.results || []);
    } catch (err) {
      console.error('获取女友列表失败:', err);
    }
  };

  // 获取作品列表
  const fetchMovies = async (filterParams = {}) => {
    try {
      const params = new URLSearchParams({
        page_size: 50,
        ordering: `-${movieFilters.sortBy}`,
        ...filterParams
      });

      if (movieFilters.search) {
        params.append('search', movieFilters.search);
      }

      const response = await fetch(`http://localhost:8000/api/movies/?${params}`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      setMovies(data.results || []);
    } catch (err) {
      console.error('获取作品列表失败:', err);
    }
  };

  // 获取女友详情
  const fetchActressDetails = async (actressId) => {
    try {
      setLoading(true);

      // 获取女友详情
      const actressResponse = await fetch(`http://localhost:8000/api/actresses/${actressId}/`);
      if (!actressResponse.ok) {
        throw new Error(`HTTP error! status: ${actressResponse.status}`);
      }
      const actressData = await actressResponse.json();
      setSelectedActress(actressData);

      // 获取女友作品
      const moviesResponse = await fetch(`http://localhost:8000/api/actresses/${actressId}/movies/`);
      if (moviesResponse.ok) {
        const moviesData = await moviesResponse.json();
        setActressMovies(moviesData.results || []);
      }

      setCurrentView('actress-detail');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // 获取作品详情
  const fetchMovieDetails = async (movieId) => {
    try {
      setLoading(true);

      const response = await fetch(`http://localhost:8000/api/movies/${movieId}/`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const movieData = await response.json();
      setSelectedMovie(movieData);
      setCurrentView('movie-detail');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // 获取统计信息
  const fetchStats = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/actresses/stats/');
      if (response.ok) {
        const statsData = await response.json();
        setStats(statsData);
      }
    } catch (err) {
      console.error('获取统计信息失败:', err);
    }
  };

  // 处理女友筛选
  const handleActressFilter = (newFilters) => {
    setActressFilters(prev => ({ ...prev, ...newFilters }));
    fetchActresses(newFilters);
  };

  // 处理作品筛选
  const handleMovieFilter = (newFilters) => {
    setMovieFilters(prev => ({ ...prev, ...newFilters }));
    fetchMovies(newFilters);
  };

  // 导航函数
  const navigateToActresses = () => {
    setCurrentView('actresses');
    setSelectedActress(null);
  };

  const navigateToMovies = () => {
    setCurrentView('movies');
    setSelectedMovie(null);
  };

  const navigateToStats = () => {
    setCurrentView('stats');
  };

  const navigateBack = () => {
    if (currentView === 'actress-detail') {
      setCurrentView('actresses');
      setSelectedActress(null);
    } else if (currentView === 'movie-detail') {
      setCurrentView('movies');
      setSelectedMovie(null);
    }
  };

  // 渲染导航栏
  const renderNavigation = () => (
    <nav className="navigation">
      <div className="nav-container">
        <h1 className="nav-title">🎬 AV Book</h1>
        <div className="nav-buttons">
          <button
            className={currentView === 'actresses' || currentView === 'actress-detail' ? 'active' : ''}
            onClick={navigateToActresses}
          >
            👩 女友列表
          </button>
          <button
            className={currentView === 'movies' || currentView === 'movie-detail' ? 'active' : ''}
            onClick={navigateToMovies}
          >
            🎬 作品库
          </button>
          <button
            className={currentView === 'stats' ? 'active' : ''}
            onClick={navigateToStats}
          >
            📊 统计信息
          </button>
        </div>
      </div>
    </nav>
  );

  // 渲染女友筛选器
  const renderActressFilters = () => (
    <div className="filters">
      <div className="filter-group">
        <input
          type="text"
          placeholder="搜索女友姓名..."
          value={actressFilters.search}
          onChange={(e) => handleActressFilter({ search: e.target.value })}
          className="search-input"
        />

        <select
          value={actressFilters.cupSize}
          onChange={(e) => handleActressFilter({ cupSize: e.target.value })}
          className="filter-select"
        >
          <option value="">所有罩杯</option>
          <option value="A">A罩杯</option>
          <option value="B">B罩杯</option>
          <option value="C">C罩杯</option>
          <option value="D">D罩杯</option>
          <option value="E">E罩杯</option>
          <option value="F">F罩杯</option>
          <option value="G">G罩杯</option>
        </select>

        <select
          value={actressFilters.heightRange}
          onChange={(e) => handleActressFilter({ heightRange: e.target.value })}
          className="filter-select"
        >
          <option value="">所有身高</option>
          <option value="short">150-160cm</option>
          <option value="medium">160-170cm</option>
          <option value="tall">170cm+</option>
        </select>

        <select
          value={actressFilters.hasPhotos}
          onChange={(e) => handleActressFilter({ hasPhotos: e.target.value })}
          className="filter-select"
        >
          <option value="">所有女友</option>
          <option value="lifestyle">有生活照</option>
          <option value="portrait">有写真照</option>
          <option value="both">有生活照和写真照</option>
        </select>

        <select
          value={actressFilters.sortBy}
          onChange={(e) => handleActressFilter({ sortBy: e.target.value })}
          className="filter-select"
        >
          <option value="name">按姓名排序</option>
          <option value="-movie_count">按作品数排序</option>
          <option value="height">按身高排序</option>
          <option value="-debut_date">按出道时间排序</option>
        </select>
      </div>
    </div>
  );

  // 渲染作品筛选器
  const renderMovieFilters = () => (
    <div className="filters">
      <div className="filter-group">
        <input
          type="text"
          placeholder="搜索作品番号或标题..."
          value={movieFilters.search}
          onChange={(e) => handleMovieFilter({ search: e.target.value })}
          className="search-input"
        />

        <select
          value={movieFilters.studio}
          onChange={(e) => handleMovieFilter({ studio: e.target.value })}
          className="filter-select"
        >
          <option value="">所有制作商</option>
          <option value="Premium">Premium</option>
          <option value="Wanz Factory">Wanz Factory</option>
          <option value="Tameike Goro">Tameike Goro</option>
          <option value="IdeaPocket">IdeaPocket</option>
          <option value="FALENO">FALENO</option>
        </select>

        <select
          value={movieFilters.year}
          onChange={(e) => handleMovieFilter({ year: e.target.value })}
          className="filter-select"
        >
          <option value="">所有年份</option>
          <option value="2024">2024年</option>
          <option value="2023">2023年</option>
          <option value="2022">2022年</option>
          <option value="2021">2021年</option>
          <option value="2020">2020年</option>
        </select>

        <select
          value={movieFilters.sortBy}
          onChange={(e) => handleMovieFilter({ sortBy: e.target.value })}
          className="filter-select"
        >
          <option value="release_date">按发行日期排序</option>
          <option value="censored_id">按番号排序</option>
          <option value="duration_minutes">按时长排序</option>
          <option value="studio">按制作商排序</option>
        </select>
      </div>
    </div>
  );

  // 渲染女友列表
  const renderActressList = () => (
    <div className="actresses-grid">
      {actresses.map(actress => (
        <div key={actress.id} className="actress-card" onClick={() => fetchActressDetails(actress.id)}>
          <div className="actress-image">
            {actress.profile_image_local ? (
              <img
                src={`http://localhost:8000/media/${actress.profile_image_local}`}
                alt={actress.name}
                onError={(e) => {
                  e.target.src = actress.profile_image || '/placeholder-avatar.jpg';
                }}
              />
            ) : actress.profile_image ? (
              <img
                src={actress.profile_image}
                alt={actress.name}
                onError={(e) => {
                  e.target.src = '/placeholder-avatar.jpg';
                }}
              />
            ) : (
              <div className="no-image">📷</div>
            )}
          </div>

          <div className="actress-info">
            <h3 className="actress-name">{actress.name}</h3>
            {actress.name_en && <p className="actress-name-en">{actress.name_en}</p>}

            <div className="actress-details">
              {actress.height && <span className="detail">📏 {actress.height}cm</span>}
              {actress.cup_size && <span className="detail">🍒 {actress.cup_size}</span>}
              {actress.measurements && <span className="detail">📐 {actress.measurements}</span>}
              {actress.birth_date && <span className="detail">🎂 {new Date(actress.birth_date).toLocaleDateString('zh-CN')}</span>}
            </div>

            <div className="actress-stats">
              <span className="stat">🎬 {actress.movie_count || 0} 作品</span>
              <span className="stat">📸 {(actress.lifestyle_photos_local_list?.length || 0) + (actress.portrait_photos_local_list?.length || 0)} 照片</span>
            </div>
          </div>

          <div className="card-hover-text">点击查看详情</div>
        </div>
      ))}
    </div>
  );

  // 渲染女友详情页
  const renderActressDetail = () => {
    if (!selectedActress) return null;

    return (
      <div className="actress-detail">
        <div className="detail-header">
          <button onClick={navigateBack} className="back-button">← 返回女友列表</button>
          <h1>{selectedActress.name}</h1>
        </div>

        <div className="detail-content">
          {/* 基本信息区域 */}
          <div className="basic-info-section">
            <div className="profile-images">
              {selectedActress.profile_image_local ? (
                <img
                  src={`http://localhost:8000/media/${selectedActress.profile_image_local}`}
                  alt={selectedActress.name}
                  className="profile-image"
                  onError={(e) => {
                    e.target.src = selectedActress.profile_image || '/placeholder-avatar.jpg';
                  }}
                />
              ) : selectedActress.profile_image ? (
                <img
                  src={selectedActress.profile_image}
                  alt={selectedActress.name}
                  className="profile-image"
                  onError={(e) => {
                    e.target.src = '/placeholder-avatar.jpg';
                  }}
                />
              ) : (
                <div className="no-image-large">📷</div>
              )}
            </div>

            <div className="basic-info">
              <h2>基本信息</h2>
              <div className="info-grid">
                <div className="info-item">
                  <span className="label">👩 中文姓名:</span>
                  <span className="value">{selectedActress.name}</span>
                </div>
                {selectedActress.name_en && (
                  <div className="info-item">
                    <span className="label">🌍 英文姓名:</span>
                    <span className="value">{selectedActress.name_en}</span>
                  </div>
                )}
                {selectedActress.height && (
                  <div className="info-item">
                    <span className="label">📏 身高:</span>
                    <span className="value">{selectedActress.height} cm</span>
                  </div>
                )}
                {selectedActress.cup_size && (
                  <div className="info-item">
                    <span className="label">🍒 罩杯:</span>
                    <span className="value">{selectedActress.cup_size}</span>
                  </div>
                )}
                {selectedActress.measurements && (
                  <div className="info-item">
                    <span className="label">📐 三围:</span>
                    <span className="value">{selectedActress.measurements}</span>
                  </div>
                )}
                {selectedActress.birth_date && (
                  <div className="info-item">
                    <span className="label">🎂 出生日期:</span>
                    <span className="value">{new Date(selectedActress.birth_date).toLocaleDateString('zh-CN')}</span>
                  </div>
                )}
                {selectedActress.birth_date && (
                  <div className="info-item">
                    <span className="label">🎈 年龄:</span>
                    <span className="value">{new Date().getFullYear() - new Date(selectedActress.birth_date).getFullYear()} 岁</span>
                  </div>
                )}
                {selectedActress.debut_date && (
                  <div className="info-item">
                    <span className="label">🌟 出道日期:</span>
                    <span className="value">{new Date(selectedActress.debut_date).toLocaleDateString('zh-CN')}</span>
                  </div>
                )}
                {selectedActress.agency && (
                  <div className="info-item">
                    <span className="label">🏢 所属事务所:</span>
                    <span className="value">{selectedActress.agency}</span>
                  </div>
                )}
                <div className="info-item">
                  <span className="label">🎬 作品总数:</span>
                  <span className="value">{actressMovies.length} 部</span>
                </div>
              </div>
            </div>
          </div>

          {/* 照片区域 - 只有真实图片时才显示 */}
          {((selectedActress.lifestyle_photos_list?.length > 0 &&
             selectedActress.lifestyle_photos_list.some(url => url && !url.includes('example.com'))) ||
            (selectedActress.portrait_photos_list?.length > 0 &&
             selectedActress.portrait_photos_list.some(url => url && !url.includes('example.com'))) ||
            (selectedActress.lifestyle_photos_local_list?.length > 0 &&
             selectedActress.lifestyle_photos_local_list.some(url => url && !url.includes('example.com'))) ||
            (selectedActress.portrait_photos_local_list?.length > 0 &&
             selectedActress.portrait_photos_local_list.some(url => url && !url.includes('example.com')))) && (
            <div className="photos-section">
              {/* 生活照 */}
              {(selectedActress.lifestyle_photos_local_list?.length > 0 || selectedActress.lifestyle_photos_list?.length > 0) && (
                <div className="photo-category">
                  <h3>🏠 生活照 ({(selectedActress.lifestyle_photos_local_list?.length || 0) + (selectedActress.lifestyle_photos_list?.length || 0)})</h3>
                  <div className="photos-grid">
                    {/* 优先显示本地照片 */}
                    {selectedActress.lifestyle_photos_local_list?.slice(0, 6).map((photo, index) => (
                      <div key={`local-${index}`} className="photo-item">
                        <img
                          src={`http://localhost:8000/media/${photo}`}
                          alt={`${selectedActress.name} 生活照 ${index + 1}`}
                          loading="lazy"
                          onError={(e) => {
                            e.target.style.display = 'none';
                          }}
                        />
                      </div>
                    ))}
                    {/* 如果本地照片不足6张，显示在线照片 */}
                    {selectedActress.lifestyle_photos_list?.slice(0, Math.max(0, 6 - (selectedActress.lifestyle_photos_local_list?.length || 0))).map((photo, index) => (
                      <div key={`online-${index}`} className="photo-item">
                        <img
                          src={photo}
                          alt={`${selectedActress.name} 生活照 ${index + 1}`}
                          loading="lazy"
                          onError={(e) => {
                            e.target.style.display = 'none';
                          }}
                        />
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 写真照 */}
              {(selectedActress.portrait_photos_local_list?.length > 0 || selectedActress.portrait_photos_list?.length > 0) && (
                <div className="photo-category">
                  <h3>🎭 写真照 ({(selectedActress.portrait_photos_local_list?.length || 0) + (selectedActress.portrait_photos_list?.length || 0)})</h3>
                  <div className="photos-grid">
                    {/* 优先显示本地照片 */}
                    {selectedActress.portrait_photos_local_list?.slice(0, 6).map((photo, index) => (
                      <div key={`local-${index}`} className="photo-item">
                        <img
                          src={`http://localhost:8000/media/${photo}`}
                          alt={`${selectedActress.name} 写真照 ${index + 1}`}
                          loading="lazy"
                          onError={(e) => {
                            e.target.style.display = 'none';
                          }}
                        />
                      </div>
                    ))}
                    {/* 如果本地照片不足6张，显示在线照片 */}
                    {selectedActress.portrait_photos_list?.slice(0, Math.max(0, 6 - (selectedActress.portrait_photos_local_list?.length || 0))).map((photo, index) => (
                      <div key={`online-${index}`} className="photo-item">
                        <img
                          src={photo}
                          alt={`${selectedActress.name} 写真照 ${index + 1}`}
                          loading="lazy"
                          onError={(e) => {
                            e.target.style.display = 'none';
                          }}
                        />
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* 相关作品 */}
          {actressMovies.length > 0 && (
            <div className="movies-section">
              <h3>🎬 相关作品 ({actressMovies.length})</h3>
              <div className="movies-grid">
                {actressMovies.map(movie => (
                  <div key={movie.id} className="movie-card" onClick={() => fetchMovieDetails(movie.id)}>
                    <div className="movie-cover">
                      {movie.cover_image_local ? (
                        <img
                          src={`http://localhost:8000/media/${movie.cover_image_local}`}
                          alt={movie.censored_id}
                          onError={(e) => {
                            e.target.src = movie.cover_image || '/placeholder-movie.jpg';
                          }}
                        />
                      ) : movie.cover_image ? (
                        <img
                          src={movie.cover_image}
                          alt={movie.censored_id}
                          onError={(e) => {
                            e.target.src = '/placeholder-movie.jpg';
                          }}
                        />
                      ) : (
                        <div className="no-image">🎬</div>
                      )}
                    </div>

                    <div className="movie-info">
                      <h4 className="movie-id">{movie.censored_id}</h4>
                      <p className="movie-title">{movie.movie_title || '暂无标题'}</p>
                      <div className="movie-details">
                        {movie.release_date && <span className="detail">📅 {new Date(movie.release_date).toLocaleDateString('zh-CN')}</span>}
                        {movie.studio && <span className="detail">🏭 {movie.studio}</span>}
                        {movie.duration_minutes && <span className="detail">⏱️ {movie.duration_minutes}分钟</span>}
                      </div>
                      {movie.movie_tags && (
                        <div className="movie-tags">
                          {movie.movie_tags.split(',').slice(0, 3).map((tag, index) => (
                            <span key={index} className="tag">{tag.trim()}</span>
                          ))}
                        </div>
                      )}

                      {/* 样品图片预览 */}
                      {(movie.sample_images_local_list?.length > 0 || movie.sample_images_list?.length > 0) && (
                        <div className="sample-images">
                          {movie.sample_images_local_list?.slice(0, 3).map((image, index) => (
                            <img
                              key={`local-${index}`}
                              src={`http://localhost:8000/media/${image}`}
                              alt={`${movie.censored_id} 样品图 ${index + 1}`}
                              className="sample-image"
                              loading="lazy"
                              onError={(e) => {
                                e.target.style.display = 'none';
                              }}
                            />
                          ))}
                          {movie.sample_images_list?.slice(0, Math.max(0, 3 - (movie.sample_images_local_list?.length || 0))).map((image, index) => (
                            <img
                              key={`online-${index}`}
                              src={image}
                              alt={`${movie.censored_id} 样品图 ${index + 1}`}
                              className="sample-image"
                              loading="lazy"
                              onError={(e) => {
                                e.target.style.display = 'none';
                              }}
                            />
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    );
  };

  // 渲染作品列表
  const renderMoviesList = () => (
    <div className="movies-grid">
      {movies.map(movie => (
        <div key={movie.id} className="movie-card" onClick={() => fetchMovieDetails(movie.id)}>
          <div className="movie-cover">
            {movie.cover_image_local ? (
              <img
                src={`http://localhost:8000/media/${movie.cover_image_local}`}
                alt={movie.censored_id}
                onError={(e) => {
                  e.target.src = movie.cover_image || '/placeholder-movie.jpg';
                }}
              />
            ) : movie.cover_image ? (
              <img
                src={movie.cover_image}
                alt={movie.censored_id}
                onError={(e) => {
                  e.target.src = '/placeholder-movie.jpg';
                }}
              />
            ) : (
              <div className="no-image">🎬</div>
            )}
          </div>

          <div className="movie-info">
            <h3 className="movie-id">{movie.censored_id}</h3>
            <p className="movie-title">{movie.movie_title}</p>

            <div className="movie-details">
              {movie.release_date && <span className="detail">📅 {new Date(movie.release_date).toLocaleDateString('zh-CN')}</span>}
              {movie.studio && <span className="detail">🏭 {movie.studio}</span>}
              {movie.duration_minutes && <span className="detail">⏱️ {movie.duration_minutes}分钟</span>}
            </div>

            {movie.actresses && movie.actresses.length > 0 && (
              <div className="movie-actresses">
                <span className="label">👩 演员:</span>
                <span className="actresses-list">
                  {movie.actresses.slice(0, 2).map(actress => actress.name).join(', ')}
                  {movie.actresses.length > 2 && ` 等${movie.actresses.length}人`}
                </span>
              </div>
            )}

            {movie.movie_tags && (
              <div className="movie-tags">
                {movie.movie_tags.split(',').slice(0, 3).map((tag, index) => (
                  <span key={index} className="tag">{tag.trim()}</span>
                ))}
              </div>
            )}

            {movie.sample_images_local_list && movie.sample_images_local_list.length > 0 && (
              <div className="sample-images">
                {movie.sample_images_local_list.slice(0, 3).map((image, index) => (
                  <img
                    key={index}
                    src={`http://localhost:8000/media/${image}`}
                    alt={`${movie.censored_id} 样品图 ${index + 1}`}
                    className="sample-image"
                    loading="lazy"
                    onError={(e) => {
                      e.target.style.display = 'none';
                    }}
                  />
                ))}
              </div>
            )}
          </div>

          <div className="card-hover-text">点击查看详情</div>
        </div>
      ))}
    </div>
  );

  // 渲染作品详情页
  const renderMovieDetail = () => {
    if (!selectedMovie) return null;

    return (
      <div className="movie-detail">
        <div className="detail-header">
          <button onClick={navigateBack} className="back-button">← 返回作品库</button>
          <h1>{selectedMovie.censored_id}</h1>
        </div>

        <div className="detail-content">
          <div className="movie-main-info">
            <div className="movie-cover-large">
              {selectedMovie.cover_image_local ? (
                <img
                  src={`http://localhost:8000/media/${selectedMovie.cover_image_local}`}
                  alt={selectedMovie.censored_id}
                  onError={(e) => {
                    e.target.src = selectedMovie.cover_image || '/placeholder-movie.jpg';
                  }}
                />
              ) : selectedMovie.cover_image ? (
                <img
                  src={selectedMovie.cover_image}
                  alt={selectedMovie.censored_id}
                  onError={(e) => {
                    e.target.src = '/placeholder-movie.jpg';
                  }}
                />
              ) : (
                <div className="no-image-large">🎬</div>
              )}
            </div>

            <div className="movie-info-detail">
              <h2>{selectedMovie.movie_title}</h2>

              <div className="info-grid">
                <div className="info-item">
                  <span className="label">🎬 番号:</span>
                  <span className="value">{selectedMovie.censored_id}</span>
                </div>
                {selectedMovie.release_date && (
                  <div className="info-item">
                    <span className="label">📅 发行日期:</span>
                    <span className="value">{new Date(selectedMovie.release_date).toLocaleDateString('zh-CN')}</span>
                  </div>
                )}
                {selectedMovie.studio && (
                  <div className="info-item">
                    <span className="label">🏭 制作商:</span>
                    <span className="value">{selectedMovie.studio}</span>
                  </div>
                )}
                {selectedMovie.duration_minutes && (
                  <div className="info-item">
                    <span className="label">⏱️ 时长:</span>
                    <span className="value">{selectedMovie.duration_minutes} 分钟</span>
                  </div>
                )}
              </div>

              {selectedMovie.movie_tags && (
                <div className="tags-section">
                  <h4>🏷️ 作品类型/标签</h4>
                  <div className="tags-list">
                    {selectedMovie.movie_tags.split(',').map((tag, index) => (
                      <span key={index} className="tag">{tag.trim()}</span>
                    ))}
                  </div>
                </div>
              )}

              {/* 作品评分和统计 */}
              <div className="movie-stats">
                <h4>📊 作品统计</h4>
                <div className="stats-row">
                  {selectedMovie.view_count && (
                    <span className="stat-item">👀 浏览: {selectedMovie.view_count}</span>
                  )}
                  {selectedMovie.download_count && (
                    <span className="stat-item">📥 下载: {selectedMovie.download_count}</span>
                  )}
                  {selectedMovie.rating && (
                    <span className="stat-item">⭐ 评分: {selectedMovie.rating}</span>
                  )}
                  {selectedMovie.magnet_count && (
                    <span className="stat-item">🧲 磁力: {selectedMovie.magnet_count}</span>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* 参演女友 */}
          {selectedMovie.actresses && selectedMovie.actresses.length > 0 && (
            <div className="actresses-section">
              <h3>👩 参演女友 ({selectedMovie.actresses.length})</h3>
              <div className="actresses-grid-small">
                {selectedMovie.actresses.map(actress => (
                  <div key={actress.id} className="actress-card-small" onClick={() => fetchActressDetails(actress.id)}>
                    <div className="actress-image-small">
                      {actress.profile_image_local ? (
                        <img
                          src={`http://localhost:8000/media/${actress.profile_image_local}`}
                          alt={actress.name}
                          onError={(e) => {
                            e.target.src = actress.profile_image || '/placeholder-avatar.jpg';
                          }}
                        />
                      ) : actress.profile_image ? (
                        <img
                          src={actress.profile_image}
                          alt={actress.name}
                          onError={(e) => {
                            e.target.src = '/placeholder-avatar.jpg';
                          }}
                        />
                      ) : (
                        <div className="no-image">📷</div>
                      )}
                    </div>
                    <span className="actress-name-small">{actress.name}</span>
                    {actress.cup_size && <span className="actress-cup-size">🍒 {actress.cup_size}</span>}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 样品图片 */}
          {(selectedMovie.sample_images_local_list?.length > 0 || selectedMovie.sample_images_list?.length > 0) && (
            <div className="samples-section">
              <h3>📸 样品图片 ({(selectedMovie.sample_images_local_list?.length || 0) + (selectedMovie.sample_images_list?.length || 0)})</h3>
              <div className="samples-grid">
                {/* 优先显示本地样品图 */}
                {selectedMovie.sample_images_local_list?.map((image, index) => (
                  <div key={`local-${index}`} className="sample-item">
                    <img
                      src={`http://localhost:8000/media/${image}`}
                      alt={`${selectedMovie.censored_id} 样品图 ${index + 1}`}
                      loading="lazy"
                      onError={(e) => {
                        e.target.style.display = 'none';
                      }}
                    />
                  </div>
                ))}
                {/* 显示在线样品图 */}
                {selectedMovie.sample_images_list?.map((image, index) => (
                  <div key={`online-${index}`} className="sample-item">
                    <img
                      src={image}
                      alt={`${selectedMovie.censored_id} 样品图 ${index + 1}`}
                      loading="lazy"
                      onError={(e) => {
                        e.target.style.display = 'none';
                      }}
                    />
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    );
  };

  // 渲染统计信息页
  const renderStats = () => (
    <div className="stats-page">
      <h2>📊 作品库统计信息</h2>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon">👩</div>
          <div className="stat-content">
            <h3>女友总数</h3>
            <div className="stat-number">{actresses.length}</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">🎬</div>
          <div className="stat-content">
            <h3>作品总数</h3>
            <div className="stat-number">{movies.length}</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">📸</div>
          <div className="stat-content">
            <h3>有头像的女友</h3>
            <div className="stat-number">
              {actresses.filter(a => a.profile_image || a.profile_image_local).length}
            </div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">🏠</div>
          <div className="stat-content">
            <h3>有生活照的女友</h3>
            <div className="stat-number">
              {actresses.filter(a => a.lifestyle_photos_local_list?.length > 0).length}
            </div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">🎭</div>
          <div className="stat-content">
            <h3>有写真照的女友</h3>
            <div className="stat-number">
              {actresses.filter(a => a.portrait_photos_local_list?.length > 0).length}
            </div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">📈</div>
          <div className="stat-content">
            <h3>平均作品数</h3>
            <div className="stat-number">
              {actresses.length > 0 ? (movies.length / actresses.length).toFixed(1) : 0}
            </div>
          </div>
        </div>
      </div>

      {/* 制作商分布 */}
      <div className="studio-stats">
        <h3>🏭 制作商分布 (前10名)</h3>
        <div className="studio-chart">
          {Object.entries(
            movies.reduce((acc, movie) => {
              if (movie.studio) {
                acc[movie.studio] = (acc[movie.studio] || 0) + 1;
              }
              return acc;
            }, {})
          )
          .sort((a, b) => b[1] - a[1])
          .slice(0, 10)
          .map(([studio, count], index) => (
            <div key={studio} className="studio-bar">
              <span className="studio-name">{studio}</span>
              <div className="bar-container">
                <div
                  className="bar"
                  style={{ width: `${(count / movies.length) * 100}%` }}
                ></div>
                <span className="count">{count}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  // 主要渲染逻辑
  if (loading && currentView !== 'actress-detail' && currentView !== 'movie-detail') {
    return (
      <div className="App">
        {renderNavigation()}
        <div className="loading">
          <div className="loading-spinner"></div>
          <p>加载中...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="App">
        {renderNavigation()}
        <div className="error">
          <h2>❌ 加载失败</h2>
          <p>{error}</p>
          <button onClick={fetchInitialData} className="retry-button">
            🔄 重试
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="App">
      {renderNavigation()}

      <main className="main-content">
        {currentView === 'actresses' && (
          <div className="actresses-page">
            {renderActressFilters()}
            <div className="page-header">
              <h2>👩 女友列表 ({actresses.length})</h2>
            </div>
            {renderActressList()}
          </div>
        )}

        {currentView === 'actress-detail' && renderActressDetail()}

        {currentView === 'movies' && (
          <div className="movies-page">
            {renderMovieFilters()}
            <div className="page-header">
              <h2>🎬 作品库 ({movies.length})</h2>
            </div>
            {renderMoviesList()}
          </div>
        )}

        {currentView === 'movie-detail' && renderMovieDetail()}

        {currentView === 'stats' && renderStats()}
      </main>
    </div>
  );
}

export default App;