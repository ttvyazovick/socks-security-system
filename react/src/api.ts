const API_URL = process.env.REACT_APP_API_URL

async function fetchApi<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    try {
        const response = await fetch(API_URL + endpoint, {
            ...options,
            headers: {
                'Accept': 'application/json',
                ...options.headers,
            },
        });

        if (!response.ok) {
            let message = `HTTP error! status: ${response.status}`;
            try {
                const errorData = await response.json();
                message = errorData.message ?? message;
            } catch {}
            throw new Error(message);
        }

        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

export async function getStats(): Promise<any> {
    return fetchApi<any>('/api/stats');
}

export async function loadSocks(query: string, offset: number, limit: number, priority: string): Promise<any> {
    const encodedQuery = encodeURIComponent(query);
    return fetchApi<any>(`/api/load?query=${encodedQuery}&offset=${offset}&limit=${limit}&priority=${priority}`);
}

export async function getWashHistory(sockId: string): Promise<any> {
    return fetchApi<any>(`/api/wash_history/${sockId}`);
}

export async function getSock(sockId: string): Promise<any> {
    return fetchApi<any>(`/api/sock/${sockId}`);
}

export async function toggleCleanStatus(sockId: string): Promise<any> {
    return fetchApi<any>(`/toggle_clean/${sockId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
    });
}

export async function deleteSock(sockId: string): Promise<any> {
    return fetchApi<any>(`/delete_sock/${sockId}`, {
        method: 'DELETE',
    });
}

export async function addSock(formData: FormData): Promise<any> {
    return fetchApi<any>('/add', {
        method: 'POST',
        body: formData,
    });
}

export async function editSock(sockId: string, formData: FormData): Promise<any> {
    return fetchApi<any>(`/edit_sock/${sockId}`, {
        method: 'POST',
        body: formData,
    });
}

export function isValidImageFile(file: File): boolean {
    const allowedTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/webp'];
    const maxSize = 1 << 24;

    if (!allowedTypes.includes(file.type)) {
        return false;
    }

    if (file.size > maxSize) {
        return false;
    }

    return true;
}
