import {
    QueryClient,
    QueryClientProvider,
}                   from '@tanstack/react-query';
import SearchScreen from './SearchScreen.jsx';

import './App.css';

const queryClient = new QueryClient({
    defaultOptions: {
        queries: {
            refetchOnWindowFocus: false,
        }
    }
});

function App() {

    return (
        <QueryClientProvider client={queryClient}>
            <SearchScreen />
        </QueryClientProvider>
    );
}

export default App;
